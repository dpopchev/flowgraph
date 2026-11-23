"""The landing of a work item: its branch merged into main, the item completed at that merge.

`fgraph land` takes the git steps a developer ran by hand: the branch merged into main, the
complete of the work item at the commit main is then on with the commit of the record, then the
worktree and the branch removed. It is part of the development: a record whose configuration
leaves the development off has no landing.

`[development] merge` of the configuration says how it merges (`flowgraph.development.way`).
Each way holds the merge uncommitted first, to complete the work item as the branch has it
before main moves.

`[development] gate` names one command a landing runs while that merge is held, once the work
item is checked to complete: a gate that fails drops the merge, so main is where it was.

`[delivery] push` pushes main to the branch it tracks twice: right after the merge, before
anything of the record is written, and again as the last step of the landing, to carry the write
that completes the work item. A first push that fails leaves the work item started and merged,
and `fgraph land` run again takes it up; a last push that fails leaves the landing as it is,
since history is never undone. `[delivery] tag` at
feature-close then tags main, the last step, when the landing completes a Feature: the tag
`fgraph release` makes (`flowgraph.development.release`), on the commit main is on, pushed after
main under `[delivery] push`. A tag that fails leaves the landing as it is too.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path

from flowgraph import work_item
from flowgraph.criterion import Decision, make_commit
from flowgraph.development import delivery
from flowgraph.development.branch import MAIN
from flowgraph.development.commit import OpenGit, Said, WorkTree, branch_started, commit_written
from flowgraph.development.gate import RunGate, check_gate
from flowgraph.development.git import GitError
from flowgraph.development.release import release_trunk
from flowgraph.development.way import Check, LandError, make_way, merged_by, removed_by
from flowgraph.feature.complete import completed_with
from flowgraph.feature.next import complete_and_start_next
from flowgraph.item.commands import ToBranch, parse_work_item_id_of_any_kind
from flowgraph.record import (
    DEVELOPMENT_ENABLED,
    GIT_COMMIT,
    Config,
    Now,
)
from flowgraph.record.store import Store
from flowgraph.work_item import WorkItemId, work_item_id_text

# A commit that stands for the merge commit while the complete is only checked.
UNMERGED = make_commit("0000000")


@dataclass(frozen=True)
class Landing:
    """What a landing works on: the store of the record, the clock and the git work tree."""

    store: Store
    now: Now
    work_tree: WorkTree


def _branch_to_land(item: str, found: Sequence[str]) -> str:
    """The one branch of the work item among those found; raises LandError for none or several."""
    if not found:
        raise LandError(f"{item} has no branch wi/{item}-* to land")
    if len(found) > 1:
        raise LandError(f"{item} has several branches to land: {', '.join(found)}")
    return found[0]


def _check_completes(item_id: WorkItemId, decision: Decision | None, landing: Landing) -> None:
    """Check that the work item can complete as the merge held brought it; raises its refusal.

    The Feature it is under is read too, as its completion reads it after main has moved: one
    the record does not hold raises FeatureNotFoundError while the merge can still be dropped.
    """
    merged = landing.store.load_work_item(item_id)
    done = work_item.completed_work_item(merged, landing.now(), UNMERGED, decision)
    completed_with(done, landing.store)


def _check_lands(completes: Check, passes: Check) -> None:
    """Check the merge held: the work item completes as it is brought, then the gate passes.

    The Tasks completed stay the first rule: a gate is not run for a work item that cannot
    complete. Raises the refusal of the first that fails.
    """
    completes()
    passes()


def _without_branch(started: ToBranch | None) -> str:
    """What a removal refused adds of the next work item the landing started: it has no branch."""
    if started is None:
        return ""
    return f"; {work_item_id_text(started.item)} is started, its branch is not"


def land_item(
    item: str,
    message: str | None,
    store: Store,
    now: Now,
    record: Path,
    open_git: OpenGit,
    config: Config,
    run_gate: RunGate,
    decision: Decision | None = None,
) -> Said:
    """Land the started work item of that id on main, by the merge of the configuration.

    The message words the commit a merge-commit or a squash makes. A Spike lands with the
    decision that answers its hypothesis, and its yes or no. The gate of the configuration, when
    it names one, is run through run_gate at the top of the work tree while the merge is held.
    Raises
    WorkItemIdError when the text is the id of no kind of work item, LandError when the
    development is off in the configuration, naming the fgraph config set that turns it on and,
    with the commits off, the one that turns them on first, when the merge
    makes a commit and no message is given or makes none and one is, when the record is outside
    a git work tree, when the work tree is not on main, when the work item has no branch or
    several or when a fast-forward finds a commit on main that the branch lacks, the refusal of
    the complete when a Task of it is not completed or its decision is missing, GateError when
    the gate exits with another status than 0, and GitError when git refuses a step. Nothing is
    merged unless main is moved; a step refused after it says how far the landing came. A record
    git ignores is completed with no commit of the record. The last work item of a started
    Feature completes the Feature in that commit of the record, named after the landing. Any
    other starts the next work item of the Feature in that commit, named after the landing too,
    and its branch is checked out at it, in a worktree of its own, once the landing is whole.
    With the push of the delivery on, main is pushed to the branch it tracks right after the
    merge, before anything of the record is written: a push git refuses leaves the work item
    started and merged, and says so; `fgraph land` run again takes it up at the commit main is on.
    Main is pushed again as the last step, to carry the write that completes the work item: that
    push refused leaves the landing whole and says main is not pushed. With the tag of the
    delivery at feature-close, a landing that completes a Feature then tags main as `fgraph
    release` does, the last step, the tag pushed under the push of the delivery: a tag refused
    leaves the landing whole and says the Feature is completed; a push of main refused makes
    no tag and says so.
    """
    item_id = parse_work_item_id_of_any_kind(item)
    text = work_item_id_text(item_id)
    if not config.development.enabled:
        commits = "" if config.git.commit else f"fgraph config set {GIT_COMMIT} true, then "
        turn_on = f"run {commits}fgraph config set {DEVELOPMENT_ENABLED} true"
        raise LandError(f"{text} cannot land: the development is off -- {turn_on}")
    way = make_way(text, config.development.merge, message)
    work_tree = open_git(record)
    if work_tree is None:
        raise LandError(f"{text} cannot land: {record} is not inside a git work tree")
    on = work_tree.current_branch()
    if on != MAIN:
        raise LandError(f"{text} lands on {MAIN}: {work_tree.path} is on {on or 'no branch'}")
    branch = _branch_to_land(text, work_tree.find_branches(f"wi/{text}-*"))
    completes = partial(_check_completes, item_id, decision, Landing(store, now, work_tree))
    passes = partial(check_gate, text, config.development.gate, work_tree.path, run_gate)
    sha = merged_by(way, text, branch, work_tree, partial(_check_lands, completes, passes))
    at_merge = delivery.pushed_at_merge(text, sha, work_tree) if config.delivery.push else ""
    written = complete_and_start_next(text, sha, store, now, config, decision)
    # The branch of the next work item is made last, once the landing is whole.
    unbranched = replace(written, branch=None)
    try:
        commit_written(unbranched, store, record, lambda _: work_tree, config)
    except GitError as error:
        raise GitError(f"{error} -- {text} is merged at {sha}, complete it there") from error
    try:
        removed_by(way, work_tree, branch)
    except GitError as error:
        landed = f"{text} is landed at {sha}, its worktree and its branch are not removed"
        raise GitError(f"{error} -- {landed}{_without_branch(written.branch)}") from error
    # What the complete says after the line of the work item: the Feature completed with it,
    # or the next work item of the Feature, started or not.
    _, _, with_it = written.out.partition("\n")
    said = f"landed {text} at {sha}\n{with_it}"
    if written.branch is not None:
        said += branch_started(written.branch, work_tree)
    feature = delivery.to_tag(config, written)
    if config.delivery.push:
        delivery.pushed(text, sha, work_tree, feature)
    said += at_merge
    if feature is not None:
        release = partial(release_trunk, None, store, record, lambda _: work_tree, config)
        said += delivery.tagged(text, sha, feature, release)
    return Said(said)
