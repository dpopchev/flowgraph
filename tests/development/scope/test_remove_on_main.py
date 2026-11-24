"""The remove of a started work item on main alone: what the check lets pass and what it names."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.development.commit import WorkTree
from flowgraph.development.remove_started import check_remove_on_main
from flowgraph.development.scope import NotOnMainError
from flowgraph.record.store import Store
from flowgraph.story import STORY
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.command

RECORD = Path("/src/project.worktrees/S-0001-a-slug/.fgraph")
HERE = Path("/src/project.worktrees/S-0001-a-slug")
HOME = Path("/src/project")
BRANCH = "wi/S-0001-a-slug"
CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def never(*_: object) -> Never:
    """A read of the record or a step of git that the check of a remove never asks for."""
    raise AssertionError("the check asks for the rows, the branch and the work tree of main")


def store(state: str) -> Store:
    """The store of a record whose Story S-0001 is in that state."""
    return Store(
        find_work_item_rows=lambda kind: (
            [WorkItemRow("S-0001", "a title", state, created=CREATED)] if kind == STORY else []
        ),
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def work_tree(branch: str) -> WorkTree:
    """A work tree at HERE on that branch, in a repository whose work tree on main is HOME."""
    return WorkTree(
        path=HERE,
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: branch,
        find_branches=never,
        find_worktree=lambda _: HOME,
        find_worktrees=never,
    )


@pytest.mark.parametrize("state", ["started", "blocked"])
def test_a_started_work_item_removed_on_a_branch_names_the_work_tree_on_main(state: str) -> None:
    with pytest.raises(
        NotOnMainError,
        match=r"^S-0001 is removed on main, in /src/project:"
        r" /src/project\.worktrees/S-0001-a-slug is on wi/S-0001-a-slug$",
    ):
        check_remove_on_main("S-0001", store(state), RECORD, lambda _: work_tree(BRANCH))


@pytest.mark.parametrize("state", ["started", "blocked"])
def test_a_started_work_item_removed_on_main_passes(state: str) -> None:
    assert check_remove_on_main("S-0001", store(state), RECORD, lambda _: work_tree("main")) is None


@pytest.mark.parametrize("state", ["backlog", "completed"])
def test_a_work_item_not_in_progress_passes_with_git_never_asked(state: str) -> None:
    assert check_remove_on_main("S-0001", store(state), RECORD, never) is None


@pytest.mark.parametrize("item", ["F-0001", "T-0001", "no-id"])
def test_a_feature_a_task_and_a_text_that_is_no_id_pass_to_the_remove(item: str) -> None:
    assert check_remove_on_main(item, store("started"), RECORD, never) is None


def test_a_record_outside_a_git_work_tree_passes() -> None:
    assert check_remove_on_main("S-0001", store("started"), RECORD, lambda _: None) is None
