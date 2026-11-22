"""The work tree that keeps a record: none outside one, and none for a record git ignores."""

from pathlib import Path
from typing import Never

import pytest

from flowgraph.development.commit import WorkTree, kept_in

pytestmark = pytest.mark.command

TOP = Path("/src/project")
RECORD = TOP / ".fgraph"


def never(*_: object) -> Never:
    """A step of git that finding the work tree of a record never asks for."""
    raise AssertionError("the work tree is asked whether git ignores the record, no more")


def work_tree(ignored: bool) -> WorkTree:
    """A work tree at TOP whose git ignores the record or not."""
    return WorkTree(
        path=TOP,
        commit_files=never,
        add_worktree=never,
        current_branch=never,
        find_branches=never,
        find_worktree=never,
        find_worktrees=never,
        ignores=lambda path: ignored and path == RECORD,
    )


def test_a_record_inside_a_work_tree_is_kept_in_it() -> None:
    tree = work_tree(ignored=False)
    assert kept_in(RECORD, lambda _: tree) == tree


def test_a_record_outside_a_work_tree_is_kept_in_none() -> None:
    assert kept_in(RECORD, lambda _: None) is None


def test_a_record_git_ignores_is_kept_in_none() -> None:
    assert kept_in(RECORD, lambda _: work_tree(ignored=True)) is None
