"""The block and the unblock of a Task of a started work item are made in its worktree.

They are refused on a branch no work item owns, main among them, before the copy that branch
holds is read, so the answer is not that of a stale file (B-0032).
"""

from pathlib import Path

from flowgraph.development.commit import OpenGit
from flowgraph.development.scope import (
    WRITTEN_IN_WORKTREE,
    OutOfScopeError,
    scope_in,
    worktree_of_item,
)
from flowgraph.record.store import KINDS, Store
from flowgraph.task import TaskIdError, parse_task_id, task_id_text
from flowgraph.work_item import IN_PROGRESS, WorkItemId, parse_work_item_id, work_item_id_text


def _holder_in_progress(task: str, store: Store) -> WorkItemId | None:
    """The started or blocked work item whose rows hold that Task; None when none does.

    The rows are read, not the copy of the item: a Task added in the worktree after the start is
    found on main too.
    """
    for kind in KINDS:
        for row in store.find_work_item_rows(kind):
            if row.state in IN_PROGRESS and any(held.id == task for held in row.tasks):
                return parse_work_item_id(kind, row.id)
    return None


def check_task_in_worktree(item: str, store: Store, record: Path, open_git: OpenGit) -> None:
    """Raise OutOfScopeError when the Task of that id is written in the worktree of its work item.

    Passes, with nothing asked of git, for an id that is no Task's and for a Task no started or
    blocked work item holds. Passes too on the branch of a work item, which answers by its own
    scope, and when the holder has no worktree; on any other branch, and on main, it raises,
    naming the holder and its worktree.
    """
    try:
        task = task_id_text(parse_task_id(item))
    except TaskIdError:
        return
    holder = _holder_in_progress(task, store)
    if holder is None or scope_in(record, open_git) is not None:
        return
    worktree = worktree_of_item(record, open_git, holder)
    if worktree is not None:
        raise OutOfScopeError(WRITTEN_IN_WORKTREE.format(work_item_id_text(holder), worktree))
