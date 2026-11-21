"""The start of a work item on main alone: what the check lets pass and what it names."""

from dataclasses import replace
from pathlib import Path
from typing import Never

import pytest

from flowgraph.commit import WorkTree
from flowgraph.scope import NotOnMainError, check_start_on_main

pytestmark = pytest.mark.command

RECORD = Path("/src/project.worktrees/ST-0001-a-slug/.fgraph")
HERE = Path("/src/project.worktrees/ST-0001-a-slug")
HOME = Path("/src/project")


def never(*_: object) -> Never:
    """A step of git that the check of a start never asks for."""
    raise AssertionError("the check asks for the branch and for the work tree of main alone")


def work_tree(branch: str, home: Path | None = HOME) -> WorkTree:
    """A work tree at HERE on that branch, in a repository whose work tree on main is home."""
    return WorkTree(
        path=HERE,
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: branch,
        find_branches=never,
        merge=never,
        abort_merge=never,
        commit_merge=never,
        find_worktree=lambda _: home,
        remove_worktree=never,
        delete_branch=never,
        find_worktrees=never,
    )


def test_a_work_item_started_on_main_passes() -> None:
    assert check_start_on_main("ST-0002", RECORD, lambda _: work_tree("main")) is None


def test_a_work_item_started_off_main_names_the_work_tree_that_is_on_main() -> None:
    with pytest.raises(
        NotOnMainError,
        match=r"^ST-0002 starts on main, in /src/project:"
        r" /src/project.worktrees/ST-0001-a-slug is on wi/ST-0001-a-slug$",
    ):
        check_start_on_main("ST-0002", RECORD, lambda _: work_tree("wi/ST-0001-a-slug"))


def test_a_work_item_started_off_main_with_no_work_tree_on_main_names_the_branch_alone() -> None:
    with pytest.raises(
        NotOnMainError,
        match=r"^ST-0002 starts on main: /src/project.worktrees/ST-0001-a-slug is on a-feature$",
    ):
        check_start_on_main("ST-0002", RECORD, lambda _: work_tree("a-feature", None))


def test_a_work_item_started_on_no_branch_says_so() -> None:
    with pytest.raises(NotOnMainError, match=r"ST-0001-a-slug is on no branch$"):
        check_start_on_main("U-0001", RECORD, lambda _: work_tree(""))


def test_a_task_started_off_main_passes() -> None:
    assert check_start_on_main("T-0001", RECORD, never) is None


def test_a_text_that_is_no_id_passes_to_the_start_that_refuses_it() -> None:
    assert check_start_on_main("no-id", RECORD, never) is None


def test_a_record_outside_a_git_work_tree_passes() -> None:
    assert check_start_on_main("ST-0002", RECORD, lambda _: None) is None


def test_a_record_git_ignores_passes_off_main() -> None:
    ignoring = replace(work_tree("a-feature"), ignores=lambda _: True)
    assert check_start_on_main("ST-0002", RECORD, lambda _: ignoring) is None
