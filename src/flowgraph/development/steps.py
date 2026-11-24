"""The steps only a landing and only a release take in a work tree, as the values they hold.

Each step is a callable bound to the work tree by open_git of flowgraph.development.commit; a
work tree built without them holds NO_LANDING and NO_RELEASE, whose every step refuses.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Never


def _lands_nothing(*_: object) -> Never:
    """A step of a landing in a work tree built without them: a contract, it lands nothing."""
    raise AssertionError("a work tree built without the steps of a landing takes none")


@dataclass(frozen=True)
class LandingSteps:
    """The steps only a landing takes in a work tree, each bound to it.

    `merge` merges a branch as a merge of its own, held uncommitted, and merges nothing when git
    refuses; it answers None while a merge is held, and the short sha of the commit the work tree
    is on when the branch brings no change; `abort_merge` drops a merge held; `commit_merge`
    commits it under a message and returns its short sha; `commit_squash` commits it as one
    commit of the branch of the work tree alone, and merges nothing when git refuses;
    `can_fast_forward` is true when a branch holds every commit the work tree is on;
    `fast_forward` moves the work tree to the tip of a branch with no commit and returns its
    short sha; `remove_worktree` and `delete_branch` remove the worktree and the branch,
    `delete_unmerged_branch` a branch whose commits the work tree does not hold; `push` pushes a
    branch to the one it tracks and returns the name of the remote; `upstream` names the remote
    a branch tracks and its ref there, refused for a branch that tracks none. `publish` pushes a
    branch, under its own name, to the remote another branch tracks and returns the name of the
    remote. Each step raises GitError when git refuses it.
    """

    merge: Callable[[str], str | None]
    abort_merge: Callable[[], None]
    commit_merge: Callable[[str], str]
    commit_squash: Callable[[str], str]
    can_fast_forward: Callable[[str], bool]
    fast_forward: Callable[[str], str]
    remove_worktree: Callable[[Path], None]
    delete_branch: Callable[[str], None]
    delete_unmerged_branch: Callable[[str], None]
    push: Callable[[str], str]
    upstream: Callable[[str], tuple[str, str]]
    publish: Callable[[str, str], str] = _lands_nothing


# The steps of a landing in a work tree built without them: each one refuses, as no such work
# tree lands.
NO_LANDING = LandingSteps(*([_lands_nothing] * 11))


def _releases_nothing(*_: object) -> Never:
    """A step of a release in a work tree built without them: a contract, it tags nothing."""
    raise AssertionError("a work tree built without the steps of a release takes none")


@dataclass(frozen=True)
class ReleaseSteps:
    """The steps only a release takes in a work tree, each bound to it.

    `find_tags` lists the tags matching a pattern; `holds_commit` is true when a tag holds a
    commit and None for a sha git does not know; `tagged_at` is when a tag was made; `make_tag`
    makes an annotated tag under a message on the head of a branch and returns the short sha of
    that commit, refused for a tag that exists; `push_tag` pushes a tag to the remote a branch
    tracks and returns the name of the remote. Each step raises GitError when git refuses it.
    """

    find_tags: Callable[[str], list[str]]
    holds_commit: Callable[[str, str], bool | None]
    tagged_at: Callable[[str], datetime]
    make_tag: Callable[[str, str, str], str]
    push_tag: Callable[[str, str], str]


# The steps of a release in a work tree built without them: each one refuses.
NO_RELEASE = ReleaseSteps(*([_releases_nothing] * 5))
