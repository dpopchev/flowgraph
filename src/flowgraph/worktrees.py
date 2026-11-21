"""The worktrees of one repository: what their records hold together.

A Task id is unique across the record, and a started work item is written in a worktree of its
own. So the next Task id is one above the highest in the record of every worktree: main and a
worktree hand out no id twice. And the row of a started work item is the one its worktree
holds, since its Tasks move there. It covers the worktrees of one repository, not two clones.
"""

from dataclasses import replace
from pathlib import Path

from flowgraph.commit import OpenGit, kept_in
from flowgraph.scope import scope_of, worktree_of_item
from flowgraph.store import OpenStore, Store
from flowgraph.work_item import Kind, WorkItemRow, parse_work_item_id

# The state of a started work item, as the record writes it.
STARTED = "started"


def across_worktrees(store: Store, record: Path, open_git: OpenGit, open_store: OpenStore) -> Store:
    """The store whose Task ids are those of the record of every worktree of the repository.

    The record of another worktree is the directory at the same path inside it as the record has
    inside its own work tree, opened by open_store. Outside a git work tree, and for a record git
    ignores, the ids are those of the record alone. The worktrees are asked for only when the ids
    are.

    Its row of a started work item is the one the worktree of its branch `wi/<id>-*` holds, as
    its file is there, committed or not. The row is that of the record itself for a work item
    without such a worktree, outside a git work tree, for a record git ignores, and in a work
    tree on the branch of a work item, which reads its own record. Git is asked only when a row
    read is started.
    """

    def find_task_ids() -> list[str]:
        work_tree = kept_in(record, open_git)
        if work_tree is None:
            return store.find_task_ids()
        top = work_tree.path.resolve()
        inside = record.resolve().relative_to(top)
        others = [path / inside for path in work_tree.find_worktrees() if path.resolve() != top]
        elsewhere = [task for other in others for task in open_store(other).find_task_ids()]
        return [*store.find_task_ids(), *elsewhere]

    def where_written(row: WorkItemRow, kind: Kind, inside: Path) -> WorkItemRow:
        worktree = worktree_of_item(record, open_git, parse_work_item_id(kind, row.id))
        if worktree is None:
            return row
        held = open_store(worktree / inside).find_work_item_rows(kind)
        return next((other for other in held if other.id == row.id), row)

    def find_work_item_rows(kind: Kind) -> list[WorkItemRow]:
        rows = store.find_work_item_rows(kind)
        if not any(row.state == STARTED for row in rows):
            return rows
        work_tree = kept_in(record, open_git)
        if work_tree is None or scope_of(work_tree.current_branch()) is not None:
            return rows
        inside = record.resolve().relative_to(work_tree.path.resolve())
        return [where_written(row, kind, inside) if row.state == STARTED else row for row in rows]

    return replace(store, find_task_ids=find_task_ids, find_work_item_rows=find_work_item_rows)
