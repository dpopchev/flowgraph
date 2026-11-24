"""The refusals of fgraph sync that are read before git runs a step."""

from dataclasses import replace
from pathlib import Path
from typing import Never

import pytest

from flowgraph.development.commit import WorkTree
from flowgraph.development.sync import SyncError, sync_branch
from flowgraph.record import make_config

pytestmark = pytest.mark.command

RECORD = Path("/src/project.worktrees/S-0001-a-slug/.fgraph")
HERE = Path("/src/project.worktrees/S-0001-a-slug")
ON = make_config("[development]\nenabled = true\n")


def never(*_: object) -> Never:
    """A step the refusals never take."""
    raise AssertionError("a refusal is read before any step of git or of the record")


def work_tree(branch: str) -> WorkTree:
    """A work tree at HERE on that branch."""
    return WorkTree(
        path=HERE,
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: branch,
        find_branches=never,
        find_worktree=never,
        find_worktrees=never,
    )


def test_the_development_off_is_refused_before_git_is_asked() -> None:
    with pytest.raises(
        SyncError,
        match=r"^fgraph sync merges main into the branch of a work item:"
        r" the development is off -- run fgraph config set development.enabled true$",
    ):
        sync_branch(RECORD, never, replace(ON, development=replace(ON.development, enabled=False)))


def test_a_record_in_no_git_work_tree_is_refused_naming_it() -> None:
    with pytest.raises(
        SyncError,
        match=rf"^fgraph sync merges main: {RECORD} is not inside a git work tree$",
    ):
        sync_branch(RECORD, lambda _: None, ON)


@pytest.mark.parametrize("branch", ["main", "topic", "wi/ZZ-0001-a-slug"])
def test_a_branch_no_work_item_owns_is_refused_naming_the_path_and_the_branch(
    branch: str,
) -> None:
    with pytest.raises(
        SyncError,
        match=rf"^fgraph sync runs on the branch of a work item, wi/<id>-<slug>:"
        rf" {HERE} is on {branch}$",
    ):
        sync_branch(RECORD, lambda _: work_tree(branch), ON)


def test_a_work_tree_on_no_branch_is_refused_as_on_no_branch() -> None:
    with pytest.raises(SyncError, match=rf"{HERE} is on no branch$"):
        sync_branch(RECORD, lambda _: work_tree(""), ON)
