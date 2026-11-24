"""The load of every worktree: a started work item is loaded whole where its Tasks are written."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.development.commit import WorkTree
from flowgraph.development.worktrees import across_worktrees
from flowgraph.record.store import Store, open_files
from flowgraph.story import make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    LoadWorkItem,
    WorkItemId,
    WorkItemNotFoundError,
    append_task,
    completed_task,
    make_work_item,
    started_task,
    started_work_item,
)

pytestmark = pytest.mark.view

HOME = Path("/src/project")
OTHER = Path("/src/project.worktrees/S-0001-a-slug")
RECORD = HOME / ".fgraph"
BRANCH = "wi/S-0001-a-slug"
ITEM = make_story_id(1)
ON = datetime(2026, 1, 1, tzinfo=UTC)
TASK = make_task(make_task_id(1), "a task title", "an output", "", ON)
QUEUED = append_task(make_work_item(ITEM, "a title", make_scenario("a", "b", "c"), "", ON), TASK)
AT_START = started_work_item(QUEUED, ON)
BEGUN = started_task(AT_START, make_task_id(1), ON)
WORKED = completed_task(BEGUN, make_task_id(1), ON, make_commit("abc1234"))
ITEMS = {RECORD: AT_START, OTHER / ".fgraph": WORKED}


def never(*_: object) -> Never:
    """A read or a write of the record, or a step of git, that loading the item never asks."""
    raise AssertionError("the item is loaded from a record and the worktree of a branch found")


def store(record: Path) -> Store:
    """The store of the record at that path, which holds the work item of ITEMS for it."""
    return Store(
        find_work_item_rows=never,
        load_work_item=lambda _: ITEMS[record],
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
        find_worktree=lambda branch: worktree if branch == BRANCH else None,
        find_worktrees=never,
    )


def written(composed: Store) -> LoadWorkItem:
    """The load_written of a composed store, narrowed from None."""
    load = composed.load_written
    if load is None:
        raise AssertionError("a store composed across the worktrees has its load_written")
    return load


def test_on_main_a_started_work_item_is_loaded_from_the_worktree_of_its_branch() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree(), store)
    assert written(shared)(ITEM) == WORKED


def test_a_started_work_item_without_a_worktree_is_loaded_from_the_record() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree(worktree=None), never)
    assert written(shared)(ITEM) == AT_START


def test_in_a_work_tree_on_its_own_branch_the_work_item_is_loaded_from_its_record() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree(on=BRANCH), never)
    assert written(shared)(ITEM) == AT_START


def test_a_record_outside_a_git_work_tree_loads_its_own_work_item() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: None, never)
    assert written(shared)(ITEM) == AT_START


def test_a_record_git_ignores_loads_its_own_work_item() -> None:
    ignoring = replace(work_tree(), ignores=lambda _: True)
    shared = across_worktrees(store(RECORD), RECORD, lambda _: ignoring, never)
    assert written(shared)(ITEM) == AT_START


def test_a_worktree_that_holds_no_file_of_it_loads_the_work_item_of_the_record() -> None:
    def lacking(item_id: WorkItemId) -> Never:
        raise WorkItemNotFoundError(item_id)

    def held_on_main(record: Path) -> Store:
        held = store(record)
        return held if record == RECORD else replace(held, load_work_item=lacking)

    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree(), held_on_main)
    assert written(shared)(ITEM) == AT_START


def test_the_composed_load_work_item_stays_the_copy_of_the_record() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree(), store)
    assert shared.load_work_item(ITEM) == AT_START


def test_a_store_of_files_has_no_load_written(tmp_path: Path) -> None:
    assert open_files(tmp_path).load_written is None
