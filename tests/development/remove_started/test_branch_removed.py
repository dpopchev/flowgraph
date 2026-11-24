"""The branch of a removed work item: removed when main holds it, left and said otherwise."""

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Never

import pytest

from flowgraph.development import GitError
from flowgraph.development.commit import LandingSteps, Said, WorkTree
from flowgraph.development.remove_started import branch_removed
from flowgraph.item.commands import Written
from flowgraph.record import make_config
from flowgraph.story import make_story_id

pytestmark = pytest.mark.command

ON = make_config("[development]\nenabled = true\n")
OFF = make_config("")
TOP = Path("/src/project")
RECORD = TOP / ".fgraph"
BRANCH = "wi/S-0001-a-slug"
WORKTREE = Path("/src/project.worktrees/S-0001-a-slug")
SAID = Said("removed S-0001\n")
MESSAGE = "chore: remove S-0001 in the record"
REMOVED = Written("removed S-0001\n", MESSAGE, unbranches=make_story_id(1))
LEFT = f"left branch {BRANCH} in {WORKTREE}: main does not hold every commit of it\n"


def never(*_: object) -> Never:
    """A step of git that the branch of the removed work item never asks for."""
    raise AssertionError("no git step is taken")


def refuse(*_: object) -> Never:
    """A git step that git refuses."""
    raise GitError("git failed: refused")


def landing(steps: list[object], held: bool = True) -> LandingSteps:
    """The landing steps of a work tree, which note each step; held says main holds its HEAD."""
    return LandingSteps(
        merge=never,
        abort_merge=never,
        commit_merge=never,
        commit_squash=never,
        can_fast_forward=lambda branch: held and branch == "main",
        fast_forward=never,
        remove_worktree=lambda path: steps.append(("remove worktree", path)),
        delete_branch=lambda branch: steps.append(("delete branch", branch)),
        delete_unmerged_branch=never,
        push=never,
        upstream=never,
    )


def tree(
    path: Path,
    steps: list[object],
    branches: Mapping[str, Path | None],
    held: bool = True,
) -> WorkTree:
    """A work tree at that path, its branches of S-0001 those given with their worktrees."""
    return WorkTree(
        path=path,
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: "main",
        find_branches=lambda pattern: list(branches) if pattern == "wi/S-0001-*" else [],
        find_worktree=lambda branch: branches.get(branch),
        find_worktrees=never,
        landing=landing(steps, held),
    )


def trees(
    steps: list[object],
    branches: Mapping[str, Path | None] | None = None,
    held: bool = True,
) -> dict[Path, WorkTree]:
    """The main tree at RECORD and one tree at each worktree, main holding them when held."""
    named = {BRANCH: WORKTREE} if branches is None else branches
    worktrees = {path: tree(path, steps, named, held) for path in named.values() if path}
    return {RECORD: tree(TOP, steps, named), **worktrees}


def said(opened: dict[Path, WorkTree]) -> Said:
    """What the remove says, git opened from the trees given, None for any other path."""
    return branch_removed(REMOVED, SAID, RECORD, opened.get, ON)


def test_main_holding_the_branch_removes_it_and_says_so() -> None:
    assert said(trees([])).out == f"removed S-0001\nremoved branch {BRANCH} in {WORKTREE}\n"


def test_main_holding_the_branch_removes_the_worktree_then_the_branch() -> None:
    steps: list[object] = []
    said(trees(steps))
    assert steps == [("remove worktree", WORKTREE), ("delete branch", BRANCH)]


def test_main_not_holding_the_branch_leaves_it_and_says_so() -> None:
    assert said(trees([], held=False)).out == f"removed S-0001\n{LEFT}"


def test_main_not_holding_the_branch_takes_no_step() -> None:
    steps: list[object] = []
    said(trees(steps, held=False))
    assert steps == []


def test_a_worktree_git_opens_none_of_is_left() -> None:
    steps: list[object] = []
    opened = {RECORD: trees(steps)[RECORD]}
    assert (said(opened).out, steps) == (f"removed S-0001\n{LEFT}", [])


def test_a_branch_with_no_worktree_is_deleted_and_said_without_a_path() -> None:
    steps: list[object] = []
    outcome = said(trees(steps, {BRANCH: None}))
    assert (outcome.out, steps) == (
        f"removed S-0001\nremoved branch {BRANCH}\n",
        [("delete branch", BRANCH)],
    )


def test_two_branches_give_two_lines() -> None:
    other = Path("/src/project.worktrees/S-0001-another-slug")
    branches: dict[str, Path | None] = {BRANCH: WORKTREE, "wi/S-0001-another-slug": other}
    assert said(trees([], branches)).out.splitlines()[1:] == [
        f"removed branch {BRANCH} in {WORKTREE}",
        f"removed branch wi/S-0001-another-slug in {other}",
    ]


def test_a_worktree_git_refuses_to_remove_is_said_and_its_branch_kept() -> None:
    steps: list[object] = []
    opened = trees(steps)
    main = opened[RECORD]
    opened[RECORD] = replace(main, landing=replace(main.landing, remove_worktree=refuse))
    with pytest.raises(GitError) as error:
        said(opened)
    assert (str(error.value), steps) == (
        f"git failed: refused -- S-0001 is removed, its branch {BRANCH} is not",
        [],
    )


def test_a_work_item_removed_from_backlog_asks_git_nothing() -> None:
    assert branch_removed(replace(REMOVED, unbranches=None), SAID, RECORD, never, ON) is SAID


def test_the_development_off_asks_git_nothing() -> None:
    assert branch_removed(REMOVED, SAID, RECORD, never, OFF) is SAID


def test_a_record_outside_a_git_work_tree_takes_no_step() -> None:
    assert branch_removed(REMOVED, SAID, RECORD, lambda _: None, ON) is SAID
