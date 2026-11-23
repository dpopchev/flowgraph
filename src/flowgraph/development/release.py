"""The release of the trunk: the next v* tag made on the head of main, annotated, and printed.

`fgraph release` takes the git steps a developer ran by hand: the tag of the release and its
push. The version is the next minor when a Story or a Bug was completed since the last v* tag,
else the next patch, and v0.1.0 when there is no tag (flowgraph.development.version); one asked
for by --version is tagged in its place. A tag is never moved or deleted: one that exists is
refused, and so is a release with nothing completed since the last tag.

A work item is completed since the last tag unless that tag holds it: by the commit it names,
which the tag holds when it is on that commit or after it, so a work item landed just before the
tag is held by it; a work item that names no commit, as one completed with the development off,
or a commit git does not know, is held when it was completed by the time the tag was made.

`[delivery] push` pushes the tag to the remote main tracks once it is made: a push that fails
leaves the tag as it is, since a tag is never deleted.

A landing tags main too (`release_landing`), before the write that completes its work item: the
version counts the kinds completed since the last tag and the kind landed, and a tag that holds
the commit of the landing, as a landing taken up finds, is the tag of it and is not made again.
"""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from flowgraph.development.branch import MAIN
from flowgraph.development.commit import OpenGit, ReleaseSteps, Said
from flowgraph.development.git import GitError
from flowgraph.development.scope import check_on_main
from flowgraph.development.version import (
    Bump,
    Version,
    bump_of,
    is_released,
    last_version,
    make_version,
    next_version,
    version_text,
)
from flowgraph.record import Config
from flowgraph.record.store import KINDS, Store
from flowgraph.work_item import Kind

# The tags a release reads and makes.
RELEASE_TAGS = "v*"

# The state a row of a completed work item is in.
COMPLETED = "completed"


class ReleaseError(Exception):
    """A release refused: outside a git work tree, of a tag that exists, or of nothing new."""


def _completed_kinds(store: Store) -> Iterator[tuple[Kind, str, datetime]]:
    """The kind, the commit and the time of each completed work item of the record."""
    for kind in KINDS:
        for row in store.find_work_item_rows(kind):
            if row.state == COMPLETED and row.completed is not None:
                yield kind, row.commit, row.completed


def _kinds_since(store: Store, last: Version | None, steps: ReleaseSteps) -> list[Kind]:
    """The kinds of the work items completed since the last tag; every completed one without it."""
    completed = list(_completed_kinds(store))
    if last is None:
        return [kind for kind, _, _ in completed]
    tag = version_text(last)
    tagged = steps.tagged_at(tag)
    return [
        kind
        for kind, commit, on in completed
        if not is_released(steps.holds_commit(tag, commit) if commit else None, on, tagged)
    ]


def _nothing_since(last: Version | None) -> str:
    """What a release with nothing completed since the last tag says."""
    since = "" if last is None else f" since {version_text(last)}"
    return f"nothing is completed{since}: no release -- complete a work item first"


def _pushed_tag(steps: ReleaseSteps, tag: str, sha: str, config: Config) -> str:
    """Push the tag of the commit under the push of the delivery; the line that names the remote.

    Nothing is said without the push. Raises GitError saying the tag is made and not pushed.
    """
    if not config.delivery.push:
        return ""
    try:
        remote = steps.push_tag(MAIN, tag)
    except GitError as error:
        raise GitError(f"{error} -- {tag} is tagged at {sha}, it is not pushed") from error
    return f"pushed {tag} to {remote}\n"


def release_trunk(
    asked: str | None, store: Store, record: Path, open_git: OpenGit, config: Config
) -> Said:
    """Tag the head of main with its next version, annotated; what fgraph says of the release.

    The version asked for is tagged in place of the next one. Raises ReleaseError when the record
    is outside a git work tree, when the version asked for is tagged already and when nothing is
    completed since the last tag; VersionError when the version asked for is none;
    NotOnMainError when the work tree of the record is not on main, as a start does; and
    GitError when git refuses a step. With the push of the delivery on, the tag is pushed to the
    remote main tracks once it is made: a push git refuses says the tag is made and not pushed.
    """
    work_tree = open_git(record)
    if work_tree is None:
        raise ReleaseError(f"fgraph release tags {MAIN}: {record} is not inside a git work tree")
    check_on_main("fgraph release", "runs", record, lambda _: work_tree)
    steps = work_tree.release
    tags = steps.find_tags(RELEASE_TAGS)
    last = last_version(tags)
    named = None if asked is None else make_version(asked)
    if named is not None and version_text(named) in tags:
        tagged = f"{version_text(named)} is tagged already: a tag is never moved or deleted"
        raise ReleaseError(f"{tagged} -- name another with --version")
    bump = bump_of(_kinds_since(store, last, steps))
    if bump is None:
        raise ReleaseError(_nothing_since(last))
    tag = version_text(next_version(last, bump) if named is None else named)
    sha = steps.make_tag(tag, f"release {tag}", MAIN)
    return Said(f"tagged {tag} at {sha}\n{_pushed_tag(steps, tag, sha, config)}")


def release_landing(kind: Kind, sha: str, store: Store, steps: ReleaseSteps, config: Config) -> str:
    """Tag main for the landing of a work item of that kind at that commit; the lines it says.

    The tag the last v* tag is when it holds the commit, as a landing taken up finds it: none is
    made. Otherwise the next version is made on main, counting the kinds completed since the last
    tag and the kind landed, which the record does not list completed yet. Under the push of the
    delivery the tag is pushed, a tag taken up again. Raises GitError saying main is not tagged
    when git refuses the tag, and that the tag is made and not pushed when it refuses the push.
    """
    last = last_version(steps.find_tags(RELEASE_TAGS))
    if last is not None and steps.holds_commit(version_text(last), sha):
        tag, at = version_text(last), sha
    else:
        bump = bump_of([*_kinds_since(store, last, steps), kind])
        tag = version_text(next_version(last, bump or Bump.PATCH))
        try:
            at = steps.make_tag(tag, f"release {tag}", MAIN)
        except GitError as error:
            raise GitError(f"{error} -- {MAIN} is not tagged {tag}") from error
    return f"tagged {tag} at {at}\n{_pushed_tag(steps, tag, at, config)}"
