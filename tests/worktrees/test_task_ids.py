"""The Task ids of every worktree: the store that names the ids of each record, with fakes."""

from dataclasses import replace
from pathlib import Path
from typing import Never

import pytest

from flowgraph.commit import WorkTree
from flowgraph.item import Store
from flowgraph.worktrees import across_worktrees

pytestmark = pytest.mark.command

HOME = Path("/src/project")
OTHER = Path("/src/project.worktrees/ST-0001-a-slug")
RECORD = HOME / ".fgraph"
IDS = {RECORD: ["T-0001", "T-0002"], OTHER / ".fgraph": ["T-0001", "T-0003"]}


def never(*_: object) -> Never:
    """A read or a write of the record, or a step of git, that naming the Task ids never asks."""
    raise AssertionError("the Task ids are read from each record and the worktrees listed, no more")


def store(record: Path) -> Store:
    """The store of the record at that path, which holds the Task ids of IDS for it."""
    return Store(
        find_work_item_rows=never,
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=lambda: IDS[record],
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def work_tree(worktrees: list[Path]) -> WorkTree:
    """The work tree at HOME of a repository with those worktrees."""
    return WorkTree(
        path=HOME,
        commit_files=never,
        add_worktree=never,
        current_branch=never,
        find_branches=never,
        merge=never,
        abort_merge=never,
        commit_merge=never,
        find_worktree=never,
        remove_worktree=never,
        delete_branch=never,
        find_worktrees=lambda: worktrees,
    )


def test_the_task_ids_are_those_of_the_record_of_every_worktree() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree([HOME, OTHER]), store)
    assert shared.find_task_ids() == ["T-0001", "T-0002", "T-0001", "T-0003"]


def test_a_repository_with_one_work_tree_names_the_ids_of_its_record() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: work_tree([HOME]), never)
    assert shared.find_task_ids() == ["T-0001", "T-0002"]


def test_a_record_outside_a_git_work_tree_names_its_own_ids() -> None:
    shared = across_worktrees(store(RECORD), RECORD, lambda _: None, never)
    assert shared.find_task_ids() == ["T-0001", "T-0002"]


def test_a_record_git_ignores_names_its_own_ids() -> None:
    ignoring = replace(work_tree([HOME, OTHER]), ignores=lambda _: True)
    shared = across_worktrees(store(RECORD), RECORD, lambda _: ignoring, never)
    assert shared.find_task_ids() == ["T-0001", "T-0002"]


def test_the_worktrees_are_not_asked_for_until_the_task_ids_are() -> None:
    assert across_worktrees(store(RECORD), RECORD, never, never).find_task_ids is not None
