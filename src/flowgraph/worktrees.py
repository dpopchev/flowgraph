"""The worktrees of one repository: what their records hold together.

A Task id is unique across the record, and a started work item is written in a worktree of its
own. So the next Task id is one above the highest in the record of every worktree: main and a
worktree hand out no id twice. And the row of a started work item, as its detail, is the one its
worktree holds, since its Tasks move there. It covers the worktrees of one repository, not two
clones.

A term is written on main alone, so the worktree of a started work item reads the terms of the
record of main: its own copy of them is the one its branch was made with.
"""

from dataclasses import replace
from pathlib import Path

from flowgraph.branch import MAIN
from flowgraph.commit import OpenGit, kept_in
from flowgraph.scope import scope_of, worktree_of_item
from flowgraph.store import OpenStore, Store
from flowgraph.term import Term
from flowgraph.work_item import (
    STARTED,
    Kind,
    WorkItemDetail,
    WorkItemId,
    WorkItemNotFoundError,
    WorkItemRow,
    parse_work_item_id,
)


def across_worktrees(store: Store, record: Path, open_git: OpenGit, open_store: OpenStore) -> Store:
    """The store whose Task ids are those of the record of every worktree of the repository.

    The record of another worktree is the directory at the same path inside it as the record has
    inside its own work tree, opened by open_store. Outside a git work tree, and for a record git
    ignores, the ids are those of the record alone. The worktrees are asked for only when the ids
    are.

    Its row of a started work item is the one the worktree of its branch `wi/<id>-*` holds, as
    its file is there, committed or not, and so is its detail. Both are those of the record
    itself for a work item without such a worktree, outside a git work tree, for a record git
    ignores, for a worktree that holds no file of it, and in a work tree on the branch of a work
    item, which reads its own record. Git is asked only when a row or the detail read is started.
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

    def inside_work_tree() -> Path | None:
        """The path of the record inside its work tree; None where the record reads itself."""
        work_tree = kept_in(record, open_git)
        if work_tree is None or scope_of(work_tree.current_branch()) is not None:
            return None
        return record.resolve().relative_to(work_tree.path.resolve())

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
        inside = inside_work_tree()
        if inside is None:
            return rows
        return [where_written(row, kind, inside) if row.state == STARTED else row for row in rows]

    def find_work_item_detail(item_id: WorkItemId) -> WorkItemDetail:
        detail = store.find_work_item_detail(item_id)
        inside = inside_work_tree() if detail.state == STARTED else None
        worktree = None if inside is None else worktree_of_item(record, open_git, item_id)
        if inside is None or worktree is None:
            return detail
        try:
            return open_store(worktree / inside).find_work_item_detail(item_id)
        except WorkItemNotFoundError:
            return detail

    def main_store() -> Store | None:
        """The store of the record of main, for a work tree on the branch of a work item."""
        work_tree = kept_in(record, open_git)
        if work_tree is None or scope_of(work_tree.current_branch()) is None:
            return None
        home = work_tree.find_worktree(MAIN)
        if home is None:
            return None
        return open_store(home / record.resolve().relative_to(work_tree.path.resolve()))

    def load_term(name: str) -> Term:
        main = main_store()
        return (store if main is None else main).terms.load_term(name)

    def find_term_names() -> list[str]:
        main = main_store()
        return (store if main is None else main).terms.find_term_names()

    terms = replace(store.terms, load_term=load_term, find_term_names=find_term_names)
    return replace(
        store,
        terms=terms,
        find_task_ids=find_task_ids,
        find_work_item_rows=find_work_item_rows,
        find_work_item_detail=find_work_item_detail,
    )
