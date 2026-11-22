"""The rows of every worktree: a started work item is read where its Tasks are written."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.commit import WorkTree
from flowgraph.item import Store
from flowgraph.story import STORY
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow
from flowgraph.worktrees import across_worktrees

pytestmark = pytest.mark.view

HOME = Path("/src/project")
OTHER = Path("/src/project.worktrees/S-0001-a-slug")
RECORD = HOME / ".fgraph"
BRANCH = "wi/S-0001-a-slug"
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
WAITING = TaskRow("T-0001", "a task title", "an output", "", "backlog")
DONE = TaskRow("T-0001", "a task title", "an output", "", "completed", "abc1234")
AT_START = WorkItemRow("S-0001", "a title", "started", created=CREATED, tasks=[WAITING])
WORKED = WorkItemRow("S-0001", "a title", "started", created=CREATED, tasks=[DONE])
QUEUED = WorkItemRow("S-0002", "another title", "backlog", created=CREATED)
ROWS = {RECORD: [AT_START, QUEUED], OTHER / ".fgraph": [WORKED]}


def never(*_: object) -> Never:
    """A read or a write of the record, or a step of git, that reading the rows never asks."""
    raise AssertionError("the rows are read from a record and the worktree of a branch found")


def store(record: Path) -> Store:
    """The store of the record at that path, which holds the rows of ROWS for it."""
    return Store(
        find_work_item_rows=lambda _: ROWS[record],
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def work_tree(on: str = "main", worktree: Path | None = OTHER) -> WorkTree:
    """The work tree at HOME, on that branch, where the branch of S-0001 has that worktree."""
    return WorkTree(
        path=HOME,
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: on,
        find_branches=lambda pattern: [BRANCH] if pattern == "wi/S-0001-*" else [],
        merge=never,
        abort_merge=never,
        commit_merge=never,
        commit_squash=never,
        can_fast_forward=never,
        fast_forward=never,
        find_worktree=lambda branch: worktree if branch == BRANCH else None,
        remove_worktree=never,
        delete_branch=never,
        delete_unmerged_branch=never,
        find_worktrees=never,
    )


def test_a_started_work_item_is_read_from_the_worktree_of_its_branch() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree(), store)
    assert shared.find_work_item_rows(STORY) == [WORKED, QUEUED]


def test_a_started_work_item_without_a_worktree_is_read_from_the_record() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree(worktree=None), never)
    assert shared.find_work_item_rows(STORY) == [AT_START, QUEUED]


def test_a_started_work_item_its_worktree_holds_no_row_of_is_read_from_the_record() -> None:
    def held_on_main(record: Path) -> Store:
        held = store(record)
        return held if record == RECORD else replace(held, find_work_item_rows=lambda _: [])

    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree(), held_on_main)
    assert shared.find_work_item_rows(STORY) == [AT_START, QUEUED]


def test_a_record_outside_a_git_work_tree_reads_its_own_rows() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: None, never)
    assert shared.find_work_item_rows(STORY) == [AT_START, QUEUED]


def test_a_record_git_ignores_reads_its_own_rows() -> None:
    ignoring = replace(work_tree(), ignores=lambda _: True)
    shared = across_worktrees(store(RECORD), RECORD, lambda _: ignoring, never)
    assert shared.find_work_item_rows(STORY) == [AT_START, QUEUED]


def test_in_the_worktree_of_a_work_item_the_rows_are_those_of_its_record() -> None:
    elsewhere = work_tree(on="wi/S-0002-another-slug")
    shared = across_worktrees(store(RECORD), RECORD, lambda _: elsewhere, never)
    assert shared.find_work_item_rows(STORY) == [AT_START, QUEUED]


def test_a_record_without_a_started_work_item_asks_git_nothing() -> None:
    held = replace(store(RECORD), find_work_item_rows=lambda _: [QUEUED])
    assert across_worktrees(held, RECORD, never, never).find_work_item_rows(STORY) == [QUEUED]
