"""The way a work item lands: the merge of the configuration, and the git steps it takes.

By `merge-commit` main gains one merge commit of the branch under the developer's message; by
`squash` one commit of its own alone that holds the work of the branch, under the message too;
by `fast-forward` main moves to the tip of the branch and no commit is made; by `pull-request`
main gains nothing from the landing, whose merge is left to a pull request on the host of the
remote. Each holds the merge uncommitted first and checks it before main moves; once landed, the
worktree and the branch go.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import assert_never

from flowgraph.criterion import DecisionError, EmptyPartError
from flowgraph.development.branch import MAIN
from flowgraph.development.commit import WorkTree
from flowgraph.development.gate import GateError
from flowgraph.development.git import GitError
from flowgraph.feature import FeatureNotFoundError
from flowgraph.record import DEVELOPMENT_MERGE, Merge
from flowgraph.task import BlockedError, CompletedAlreadyError, NotStartedError, OpenTaskError
from flowgraph.work_item import RemovedAlreadyError, WorkItemNotFoundError

# What stops a merge held from being committed: a refusal of the complete, of the gate or of git.
NOT_COMMITTED = (
    WorkItemNotFoundError,
    FeatureNotFoundError,
    NotStartedError,
    BlockedError,
    OpenTaskError,
    CompletedAlreadyError,
    RemovedAlreadyError,
    DecisionError,
    EmptyPartError,
    GateError,
    GitError,
)


@dataclass(frozen=True)
class MergeCommit:
    """A landing by one merge commit of the branch on main, under the developer's message."""

    message: str


@dataclass(frozen=True)
class Squash:
    """A landing by one commit of main alone holding the work of the branch, under the message."""

    message: str


@dataclass(frozen=True)
class FastForward:
    """A landing that moves main to the tip of the branch: it makes no commit to word."""


@dataclass(frozen=True)
class PullRequest:
    """A landing left to a pull request on the host of the remote: it makes no commit to word."""


# How a work item lands: the merge of the configuration, with the message of the commit it makes.
Way = MergeCommit | Squash | FastForward | PullRequest

# Check the merge held, as the tree main will have: raises the refusal of what it checks.
Check = Callable[[], None]


class LandError(Exception):
    """A landing refused before anything is merged; the message says why."""


def _worded(item: str, merge: Merge, message: str | None) -> str:
    """The message of the commit a landing by that merge makes; raises LandError without one."""
    if message is None:
        makes = f"{DEVELOPMENT_MERGE} = {merge.value} makes a commit to word"
        raise LandError(f"{item} cannot land without --message: {makes}")
    return message


def _unworded(item: str, merge: Merge, message: str | None) -> None:
    """Check a landing by that merge, which makes no commit, has no message; raises LandError."""
    if message is not None:
        makes = f"{DEVELOPMENT_MERGE} = {merge.value} makes no commit to word"
        raise LandError(f"{item} cannot land with --message: {makes}")


def make_way(item: str, merge: Merge, message: str | None) -> Way:
    """How the work item of that id lands: the merge of the configuration, with its message.

    Raises LandError naming the key when a merge that makes a commit has no message to word it,
    and when a fast-forward or a pull request, which make none, is given one.
    """
    match merge:
        case Merge.MERGE_COMMIT:
            return MergeCommit(_worded(item, merge, message))
        case Merge.SQUASH:
            return Squash(_worded(item, merge, message))
        case Merge.FAST_FORWARD:
            _unworded(item, merge, message)
            return FastForward()
        case Merge.PULL_REQUEST:
            _unworded(item, merge, message)
            return PullRequest()
        case _ as unreachable:
            assert_never(unreachable)


def _committed(work_tree: WorkTree, branch: str, check: Check, commit: Callable[[], str]) -> str:
    """Hold the merge of the branch, check it, then commit it; the sha of that commit.

    A branch that brings no change is merged already: the check runs and the sha main is on is
    answered, with no commit. Raises the refusal of the check, or GitError when git refuses the
    merge or the commit; the merge held is dropped then, and so it is when Ctrl-C interrupts the
    check, as under a gate.
    """
    taken = work_tree.landing.merge(branch)
    if taken is not None:
        check()
        return taken
    try:
        check()
        return commit()
    except (*NOT_COMMITTED, KeyboardInterrupt):
        work_tree.landing.abort_merge()
        raise


def _held(work_tree: WorkTree, branch: str, check: Check) -> str | None:
    """Hold the merge of the branch, check it and drop it; the sha main is on, or None.

    A branch that brings no change answers the sha main is on once checked, with nothing held;
    None is answered once a merge held is checked and dropped. Raises the refusal of the check,
    or GitError when git refuses a step; the merge held is dropped then too.
    """
    taken = work_tree.landing.merge(branch)
    if taken is not None:
        check()
        return taken
    try:
        check()
    finally:
        work_tree.landing.abort_merge()
    return None


def _fast_forwarded(work_tree: WorkTree, branch: str, check: Check) -> str:
    """Hold the merge of the branch to check it, drop it, then move main to the tip; its sha.

    A fast-forward cannot be held, so the merge held is the one look at the record of the branch
    and at the tree the gate runs on before main moves. Raises the refusal of the check, or
    GitError when git refuses a step; main is where it was then. A branch main holds already
    brings no change: the check runs and the sha main is on is answered, with no fast-forward.
    """
    taken = _held(work_tree, branch, check)
    if taken is not None:
        return taken
    return work_tree.landing.fast_forward(branch)


def merged_by(way: Way, item: str, branch: str, work_tree: WorkTree, check: Check) -> str | None:
    """Merge the branch into main by the way, once the check holds; the commit main is then on.

    A branch merged into main already, by hand or by a landing that stopped after its merge, is
    taken up at the commit main is on: the check runs, no merge is made. A pull request merges
    nothing: its merge is held, checked and dropped, and None is answered while main lacks the
    branch. Raises LandError when a fast-forward finds a commit on main that the branch lacks,
    the refusal of the check, or GitError when git refuses a step; nothing is merged then.
    """
    steps = work_tree.landing
    match way:
        case MergeCommit(message):
            return _committed(work_tree, branch, check, partial(steps.commit_merge, message))
        case Squash(message):
            return _committed(work_tree, branch, check, partial(steps.commit_squash, message))
        case FastForward():
            if not steps.can_fast_forward(branch):
                bring = f"rebase {branch} on {MAIN} or merge {MAIN} into it"
                lacks = f"{MAIN} holds a commit {branch} lacks"
                raise LandError(f"{item} cannot land by fast-forward: {lacks} -- {bring}")
            return _fast_forwarded(work_tree, branch, check)
        case PullRequest():
            return _held(work_tree, branch, check)
        case _ as unreachable:
            assert_never(unreachable)


def removed_by(way: Way, work_tree: WorkTree, branch: str) -> None:
    """Remove the worktree of the branch, when it has one, then the branch; raises GitError.

    Main holds no commit of a branch landed by squash, so git deletes it as an unmerged one; so
    it does a branch landed through a pull request, which the host may rebase or squash.
    """
    worktree = work_tree.find_worktree(branch)
    if worktree is not None:
        work_tree.landing.remove_worktree(worktree)
    match way:
        case MergeCommit() | FastForward():
            work_tree.landing.delete_branch(branch)
        case Squash() | PullRequest():
            work_tree.landing.delete_unmerged_branch(branch)
        case _ as unreachable:
            assert_never(unreachable)
