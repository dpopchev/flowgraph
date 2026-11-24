"""The check of a Task of a started work item: its block and unblock are made in its worktree."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.bug import BUG
from flowgraph.development.commit import WorkTree
from flowgraph.development.scope import OutOfScopeError
from flowgraph.development.task_scope import check_task_in_worktree
from flowgraph.item.commands import Store
from flowgraph.story import STORY
from flowgraph.task import TaskRow
from flowgraph.work_item import Kind, WorkItemRow

pytestmark = pytest.mark.command

HOME = Path("/src/project")
RECORD = HOME / ".fgraph"
OTHER = Path("/src/project.worktrees/S-0001-a-slug")
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
STARTED_TASK = TaskRow("T-0001", "a task title", "an output", "", "started")
STARTED = WorkItemRow("S-0001", "a title", "started", created=CREATED, tasks=[STARTED_TASK])
BLOCKED = WorkItemRow("S-0001", "a title", "blocked", created=CREATED, tasks=[STARTED_TASK])
BACKLOG = WorkItemRow(
    "S-0001",
    "a title",
    "backlog",
    created=CREATED,
    tasks=[TaskRow("T-0001", "a task title", "an output", "", "backlog")],
)
COMPLETED = WorkItemRow("S-0001", "a title", "completed", created=CREATED, tasks=[])


def never(*_: object) -> Never:
    """A read of the record, or a step of git, that the check never asks for."""
    raise AssertionError("the check reads the rows of the record and asks git for a worktree")


def unread() -> Store:
    """A store whose every read and write is never: the check of an id that is no Task asks none."""
    return Store(
        find_work_item_rows=never,
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def store(kind: Kind, rows: list[WorkItemRow]) -> Store:
    """A store whose rows of that kind are `rows`, and of every other kind none."""
    return replace(unread(), find_work_item_rows=lambda found: rows if found == kind else [])


def work_tree(on: str = "main", worktree: Path | None = OTHER, owner: str = "S-0001") -> WorkTree:
    """The work tree at HOME, on that branch, where the branch of that work item has a worktree."""
    branch = f"wi/{owner}-a-slug"
    return WorkTree(
        path=HOME,
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: on,
        find_branches=lambda pattern: [branch] if pattern == f"wi/{owner}-*" else [],
        find_worktree=lambda found: worktree if found == branch else None,
        find_worktrees=never,
    )


def test_a_task_of_a_started_work_item_with_a_worktree_is_refused_on_main() -> None:
    with pytest.raises(
        OutOfScopeError,
        match=r"^S-0001 is started: its Tasks are written in its worktree, /src/project\.worktrees/"
        r"S-0001-a-slug$",
    ):
        check_task_in_worktree("T-0001", store(STORY, [STARTED]), RECORD, lambda _: work_tree())


def test_a_task_of_a_blocked_work_item_with_a_worktree_is_refused_on_main() -> None:
    with pytest.raises(
        OutOfScopeError,
        match=r"^S-0001 is started: its Tasks are written in its worktree, /src/project\.worktrees/"
        r"S-0001-a-slug$",
    ):
        check_task_in_worktree("T-0001", store(STORY, [BLOCKED]), RECORD, lambda _: work_tree())


def test_a_task_of_a_started_work_item_is_refused_on_a_branch_no_work_item_owns() -> None:
    with pytest.raises(OutOfScopeError, match=r"^S-0001 is started: its Tasks are written"):
        check_task_in_worktree(
            "T-0001", store(STORY, [STARTED]), RECORD, lambda _: work_tree(on="a-feature")
        )


def test_a_task_of_a_started_bug_is_refused_naming_the_bug() -> None:
    bug = WorkItemRow("B-0001", "a title", "started", created=CREATED, tasks=[STARTED_TASK])
    with pytest.raises(OutOfScopeError, match=r"^B-0001 is started: its Tasks are written"):
        check_task_in_worktree(
            "T-0001", store(BUG, [bug]), RECORD, lambda _: work_tree(on="a-feature", owner="B-0001")
        )


def test_a_task_of_a_started_work_item_without_a_worktree_is_not_refused() -> None:
    result = check_task_in_worktree(
        "T-0001", store(STORY, [STARTED]), RECORD, lambda _: work_tree(worktree=None)
    )
    assert result is None


def test_a_task_checked_on_the_branch_of_its_work_item_is_not_refused() -> None:
    result = check_task_in_worktree(
        "T-0001",
        store(STORY, [STARTED]),
        RECORD,
        lambda _: work_tree(on="wi/S-0001-a-slug"),
    )
    assert result is None


def test_a_task_checked_on_the_branch_of_another_work_item_is_not_refused() -> None:
    result = check_task_in_worktree(
        "T-0001",
        store(STORY, [STARTED]),
        RECORD,
        lambda _: work_tree(on="wi/S-0002-another-slug"),
    )
    assert result is None


def test_a_task_in_a_record_outside_a_git_work_tree_is_not_refused() -> None:
    result = check_task_in_worktree("T-0001", store(STORY, [STARTED]), RECORD, lambda _: None)
    assert result is None


def test_a_task_in_a_record_git_ignores_is_not_refused() -> None:
    ignoring = replace(work_tree(), ignores=lambda _: True)
    result = check_task_in_worktree("T-0001", store(STORY, [STARTED]), RECORD, lambda _: ignoring)
    assert result is None


def test_a_task_of_a_work_item_in_backlog_asks_git_nothing() -> None:
    result = check_task_in_worktree("T-0001", store(STORY, [BACKLOG]), RECORD, never)
    assert result is None


def test_a_task_of_a_completed_work_item_asks_git_nothing() -> None:
    result = check_task_in_worktree("T-0001", store(STORY, [COMPLETED]), RECORD, never)
    assert result is None


def test_a_task_no_row_holds_asks_git_nothing() -> None:
    result = check_task_in_worktree("T-0009", store(STORY, [STARTED]), RECORD, never)
    assert result is None


@pytest.mark.parametrize("item", ["S-0001", "F-0001", "T-0000", "no-id"])
def test_an_item_that_is_not_a_task_id_asks_the_store_and_git_nothing(item: str) -> None:
    result = check_task_in_worktree(item, unread(), RECORD, never)
    assert result is None
