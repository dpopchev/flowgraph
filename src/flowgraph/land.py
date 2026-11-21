"""The landing of a work item: its branch merged into main, the item completed at that merge.

`fgraph land` takes the git steps a developer ran by hand: one merge commit of the branch on
main under the developer's message, the complete of the work item at that commit with the
commit of the record, then the worktree and the branch removed.
"""

from collections.abc import Sequence
from pathlib import Path

from flowgraph import work_item
from flowgraph.branch import MAIN, GitError
from flowgraph.commit import OpenGit, Said, WorkTree, commit_written
from flowgraph.criterion import make_commit
from flowgraph.item import complete_item, parse_work_item_id_of_any_kind
from flowgraph.record import Now
from flowgraph.store import Store
from flowgraph.task import CompletedAlreadyError, NotStartedError, OpenTaskError
from flowgraph.work_item import WorkItemId, WorkItemNotFoundError, work_item_id_text

# A commit that stands for the merge commit while the complete is only checked.
UNMERGED = make_commit("0000000")

# What stops a merge held from being committed: a refusal of the complete, or of git.
NOT_COMMITTED = (
    WorkItemNotFoundError,
    NotStartedError,
    OpenTaskError,
    CompletedAlreadyError,
    GitError,
)


class LandError(Exception):
    """A landing refused before anything is merged; the message says why."""


def _branch_to_land(item: str, found: Sequence[str]) -> str:
    """The one branch of the work item among those found; raises LandError for none or several."""
    if not found:
        raise LandError(f"{item} has no branch wi/{item}-* to land")
    if len(found) > 1:
        raise LandError(f"{item} has several branches to land: {', '.join(found)}")
    return found[0]


def _merge_committed(
    item_id: WorkItemId, message: str, store: Store, now: Now, work_tree: WorkTree
) -> str:
    """Commit the merge held under the message, once the merged work item can complete; its sha.

    Raises the refusal of the complete, or GitError when git refuses the commit.
    """
    work_item.completed_work_item(store.load_work_item(item_id), now(), UNMERGED)
    return work_tree.commit_merge(message)


def _removed(work_tree: WorkTree, branch: str) -> None:
    """Remove the worktree of the branch, when it has one, then the branch; raises GitError."""
    worktree = work_tree.find_worktree(branch)
    if worktree is not None:
        work_tree.remove_worktree(worktree)
    work_tree.delete_branch(branch)


def land_item(
    item: str, message: str, store: Store, now: Now, record: Path, open_git: OpenGit
) -> Said:
    """Land the started work item of that id on main under the message; what fgraph says.

    Raises WorkItemIdError when the text is the id of no kind of work item, LandError when the
    record is outside a git work tree, when the work tree is not on main or when the work item
    has no branch or several, the refusal of the complete when a Task of it is not completed,
    and GitError when git refuses a step. Nothing is merged unless the merge is committed; a
    step refused after it says how far the landing came.
    """
    item_id = parse_work_item_id_of_any_kind(item)
    text = work_item_id_text(item_id)
    work_tree = open_git(record)
    if work_tree is None:
        raise LandError(f"{text} cannot land: {record} is not inside a git work tree")
    on = work_tree.current_branch()
    if on != MAIN:
        raise LandError(f"{text} lands on {MAIN}: {work_tree.path} is on {on or 'no branch'}")
    branch = _branch_to_land(text, work_tree.find_branches(f"wi/{text}-*"))
    work_tree.merge(branch)
    try:
        sha = _merge_committed(item_id, message, store, now, work_tree)
    except NOT_COMMITTED:
        work_tree.abort_merge()
        raise
    written = complete_item(text, sha, store, now)
    try:
        commit_written(written, store, record, lambda _: work_tree)
    except GitError as error:
        raise GitError(f"{error} -- {text} is merged at {sha}, complete it there") from error
    try:
        _removed(work_tree, branch)
    except GitError as error:
        landed = f"{text} is landed at {sha}"
        raise GitError(
            f"{error} -- {landed}, its worktree and its branch are not removed"
        ) from error
    return Said(f"landed {text} at {sha}\n")
