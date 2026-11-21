"""The scope of main: a Task write of a started work item is refused outside its worktree."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.commit import WorkTree
from flowgraph.criterion import make_commit, make_scenario
from flowgraph.item import Store
from flowgraph.scope import OutOfScopeError, Scope, within, worktree_of_item
from flowgraph.story import make_story, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    completed_task,
    completed_work_item,
    started_task,
    started_work_item,
)

pytestmark = pytest.mark.command

RECORD = Path("/src/project/.fgraph")
WORKTREE = Path("/src/project.worktrees/ST-0001-a-slug")
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
ONE = make_story_id(1)
TASK = make_task(make_task_id(1), "a task", "an output", "", CREATED)
STORY = append_task(make_story(ONE, "a title", make_scenario("a", "b", "c"), "", CREATED), TASK)
BEGUN = started_work_item(STORY, NOW)
MOVED = started_task(BEGUN, make_task_id(1), NOW)
DONE = completed_task(MOVED, make_task_id(1), NOW, make_commit("abc1234"))
LANDED = completed_work_item(DONE, NOW, make_commit("3e9ae5c"))


def never(*_: object) -> Never:
    """A read of the record, or a step of git, that the scope of main never asks for."""
    raise AssertionError("the scope loads the work item saved and asks for its worktree alone")


def store(held: WorkItemState, saved: list[WorkItemState]) -> Store:
    """A store holding that work item, which notes what it saves."""
    return Store(
        find_work_item_rows=never,
        load_work_item=lambda _: held,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=saved.append,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def work_tree(branches: list[str], worktree: Path | None) -> WorkTree:
    """A work tree of a repository holding those branches, each checked out in that worktree."""
    return WorkTree(
        path=Path("/src/project"),
        commit_files=never,
        add_worktree=never,
        current_branch=never,
        find_branches=lambda pattern: branches if pattern == "wi/ST-0001-*" else [],
        merge=never,
        abort_merge=never,
        commit_merge=never,
        find_worktree=lambda _: worktree,
        remove_worktree=never,
        delete_branch=never,
        find_worktrees=never,
    )


def test_a_task_write_of_a_started_work_item_with_a_worktree_is_refused_naming_it() -> None:
    with pytest.raises(
        OutOfScopeError,
        match=r"^ST-0001 is started: its Tasks are written in its worktree,"
        r" /src/project.worktrees/ST-0001-a-slug$",
    ):
        within(store(BEGUN, []), lambda: None, lambda _: WORKTREE).save_work_item(MOVED)


def test_a_task_write_refused_is_not_saved() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(OutOfScopeError):
        within(store(BEGUN, saved), lambda: None, lambda _: WORKTREE).save_work_item(MOVED)
    assert saved == []


def test_a_task_write_of_a_started_work_item_without_a_worktree_is_saved() -> None:
    saved: list[WorkItemState] = []
    within(store(BEGUN, saved), lambda: None, lambda _: None).save_work_item(MOVED)
    assert saved == [MOVED]


def test_the_start_of_a_work_item_is_saved() -> None:
    saved: list[WorkItemState] = []
    within(store(STORY, saved), lambda: None, never).save_work_item(BEGUN)
    assert saved == [BEGUN]


def test_the_complete_of_a_work_item_is_saved() -> None:
    saved: list[WorkItemState] = []
    within(store(DONE, saved), lambda: None, never).save_work_item(LANDED)
    assert saved == [LANDED]


def test_a_task_write_on_the_branch_of_the_work_item_is_saved() -> None:
    saved: list[WorkItemState] = []
    own = Scope("wi/ST-0001-a-slug", ONE)
    within(store(BEGUN, saved), lambda: own, never).save_work_item(MOVED)
    assert saved == [MOVED]


def test_the_worktree_of_a_work_item_is_the_one_its_branch_is_checked_out_in() -> None:
    tree = work_tree(["wi/ST-0001-a-slug"], WORKTREE)
    assert worktree_of_item(RECORD, lambda _: tree, ONE) == WORKTREE


def test_a_work_item_whose_branch_is_in_no_worktree_has_none() -> None:
    tree = work_tree(["wi/ST-0001-a-slug"], None)
    assert worktree_of_item(RECORD, lambda _: tree, ONE) is None


def test_a_work_item_without_a_branch_has_no_worktree() -> None:
    assert worktree_of_item(RECORD, lambda _: work_tree([], WORKTREE), ONE) is None


def test_a_record_outside_a_git_work_tree_has_no_worktree_of_a_work_item() -> None:
    assert worktree_of_item(RECORD, lambda _: None, ONE) is None


def test_a_record_git_ignores_has_no_worktree_of_a_work_item() -> None:
    ignoring = replace(work_tree(["wi/ST-0001-a-slug"], WORKTREE), ignores=lambda _: True)
    assert worktree_of_item(RECORD, lambda _: ignoring, ONE) is None
