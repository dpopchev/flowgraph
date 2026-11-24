"""The record of main, found from the record kept in the work tree of a work item."""

from dataclasses import replace
from pathlib import Path
from typing import Never

import pytest

from flowgraph.development.branch import MAIN
from flowgraph.development.commit import WorkTree
from flowgraph.development.worktrees import record_of_main

pytestmark = pytest.mark.view

HOME = Path("/src/project")
OTHER = Path("/src/project.worktrees/S-0001-a-slug")
BRANCH = "wi/S-0001-a-slug"


def never(*_: object) -> Never:
    """A step of git that finding the record of main never asks for."""
    raise AssertionError("the record of main is found from the work tree that keeps the record")


def work_tree(on: str = BRANCH, home: Path | None = HOME) -> WorkTree:
    """The work tree at OTHER, on that branch, with main checked out at home when home is set."""
    return WorkTree(
        path=OTHER,
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: on,
        find_branches=never,
        find_worktree=lambda branch: home if branch == MAIN else None,
        find_worktrees=never,
    )


def test_on_the_branch_of_a_work_item_the_record_of_main_is_the_one_at_home() -> None:
    assert record_of_main(OTHER / ".fgraph", lambda _: work_tree()) == HOME / ".fgraph"


def test_a_record_deeper_in_the_work_tree_is_found_at_the_same_depth_at_home() -> None:
    assert record_of_main(OTHER / "docs" / ".fgraph", lambda _: work_tree()) == (
        HOME / "docs" / ".fgraph"
    )


def test_on_main_there_is_no_record_of_main() -> None:
    main = replace(work_tree(on=MAIN), find_worktree=never)
    assert record_of_main(OTHER / ".fgraph", lambda _: main) is None


def test_on_a_branch_no_work_item_owns_there_is_no_record_of_main() -> None:
    assert record_of_main(OTHER / ".fgraph", lambda _: work_tree(on="feature/other")) is None


def test_on_no_branch_there_is_no_record_of_main() -> None:
    assert record_of_main(OTHER / ".fgraph", lambda _: work_tree(on="")) is None


def test_outside_a_git_work_tree_there_is_no_record_of_main() -> None:
    assert record_of_main(OTHER / ".fgraph", lambda _: None) is None


def test_for_a_record_git_ignores_there_is_no_record_of_main() -> None:
    ignoring = replace(work_tree(), ignores=lambda _: True)
    assert record_of_main(OTHER / ".fgraph", lambda _: ignoring) is None


def test_with_no_work_tree_on_main_there_is_no_record_of_main() -> None:
    assert record_of_main(OTHER / ".fgraph", lambda _: work_tree(home=None)) is None
