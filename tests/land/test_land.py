"""The landing of a work item: its git steps in order and what it refuses, with fakes."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.branch import GitError
from flowgraph.commit import Said, WorkTree
from flowgraph.config import Config, make_config
from flowgraph.criterion import make_commit, make_scenario
from flowgraph.item import Store
from flowgraph.land import LandError, land_item
from flowgraph.story import make_story, make_story_id
from flowgraph.task import OpenTaskError, make_task, make_task_id
from flowgraph.work_item import (
    CompletedWorkItem,
    WorkItemState,
    append_task,
    completed_task,
    started_task,
    started_work_item,
)

pytestmark = pytest.mark.command

ON = make_config("[development]\nenabled = true\n")
OFF = make_config("")
TOP = Path("/src/project")
RECORD = TOP / ".fgraph"
FILE = RECORD / "items" / "S-0001.toml"
BRANCH = "wi/S-0001-a-slug"
WORKTREE = Path("/src/project.worktrees/S-0001-a-slug")
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
TASK = make_task(make_task_id(1), "a task", "an output", "", CREATED)
STORY = make_story(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
OPEN = started_task(started_work_item(append_task(STORY, TASK), NOW), make_task_id(1), NOW)
READY = completed_task(OPEN, make_task_id(1), NOW, make_commit("abc1234"))
MESSAGE = "feat: land the first Story"


def never(*_: object) -> Never:
    """A read or a write of the record that a landing never asks for."""
    raise AssertionError("a landing loads the work item, saves it and names its file")


def refuse(*_: object) -> Never:
    """A git step that git refuses."""
    raise GitError("git failed: refused")


def store(item: WorkItemState, saved: list[WorkItemState] | None = None) -> Store:
    """The store of a record holding that work item, whose save changes its file."""
    kept = [] if saved is None else saved
    return Store(
        find_work_item_rows=never,
        load_work_item=lambda _: item,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=kept.append,
        load_queue=never,
        save_queue=never,
        find_changed_files=lambda: [FILE],
        restore_files=lambda: None,
    )


def work_tree(steps: list[object]) -> WorkTree:
    """A work tree at TOP on main holding BRANCH in WORKTREE; it notes each step it takes."""

    def commit_files(files: Sequence[Path], message: str) -> str:
        steps.append(("commit", [str(file) for file in files], message))
        return "0000000"

    def commit_merge(message: str) -> str:
        steps.append(("commit merge", message))
        return "3e9ae5c"

    return WorkTree(
        path=TOP,
        commit_files=commit_files,
        add_worktree=never,
        current_branch=lambda: "main",
        find_branches=lambda _: [BRANCH],
        merge=lambda branch: steps.append(("merge", branch)),
        abort_merge=lambda: steps.append("abort merge"),
        commit_merge=commit_merge,
        find_worktree=lambda _: WORKTREE,
        remove_worktree=lambda path: steps.append(("remove worktree", path)),
        delete_branch=lambda branch: steps.append(("delete branch", branch)),
        find_worktrees=never,
    )


def land(
    item: WorkItemState,
    tree: WorkTree | None,
    saved: list[WorkItemState] | None = None,
    config: Config = ON,
) -> Said:
    """Land S-0001 on the record holding that work item, in that work tree, the development on."""
    kept = store(item, saved)
    return land_item("S-0001", MESSAGE, kept, lambda: NOW, RECORD, lambda _: tree, config)


def test_a_landing_with_the_development_off_is_refused_naming_the_key() -> None:
    with pytest.raises(LandError) as error:
        land(READY, work_tree([]), config=OFF)
    assert str(error.value) == (
        "S-0001 cannot land: the development is off"
        " -- set development.enabled = true in /src/project/.fgraph/config.toml"
    )


def test_a_landing_with_the_development_off_takes_no_git_step() -> None:
    steps: list[object] = []
    with pytest.raises(LandError):
        land(READY, work_tree(steps), config=OFF)
    assert steps == []


def test_a_landing_takes_its_git_steps_in_order() -> None:
    steps: list[object] = []
    land(READY, work_tree(steps))
    assert steps == [
        ("merge", BRANCH),
        ("commit merge", MESSAGE),
        ("commit", [".fgraph/items/S-0001.toml"], "chore: complete S-0001 in the record"),
        ("remove worktree", WORKTREE),
        ("delete branch", BRANCH),
    ]


def test_a_landing_names_the_work_item_and_the_merge_commit() -> None:
    assert land(READY, work_tree([])) == Said("landed S-0001 at 3e9ae5c\n")


def test_a_landing_completes_the_work_item_at_the_merge_commit() -> None:
    saved: list[WorkItemState] = []
    land(READY, work_tree([]), saved)
    assert [(type(item), item.commit) for item in saved if isinstance(item, CompletedWorkItem)] == [
        (CompletedWorkItem, make_commit("3e9ae5c"))
    ]


def test_a_branch_without_a_worktree_is_deleted_alone() -> None:
    steps: list[object] = []
    land(READY, replace(work_tree(steps), find_worktree=lambda _: None))
    assert steps[-2:] == [
        ("commit", [".fgraph/items/S-0001.toml"], "chore: complete S-0001 in the record"),
        ("delete branch", BRANCH),
    ]


def test_a_landing_with_a_task_not_completed_aborts_the_merge() -> None:
    steps: list[object] = []
    with pytest.raises(OpenTaskError):
        land(OPEN, work_tree(steps))
    assert steps == [("merge", BRANCH), "abort merge"]


def test_a_merge_commit_git_refuses_aborts_the_merge() -> None:
    steps: list[object] = []
    with pytest.raises(GitError):
        land(READY, replace(work_tree(steps), commit_merge=refuse))
    assert steps == [("merge", BRANCH), "abort merge"]


def test_a_merge_git_refuses_takes_no_other_step() -> None:
    steps: list[object] = []
    with pytest.raises(GitError):
        land(READY, replace(work_tree(steps), merge=refuse))
    assert steps == []


def test_a_landing_outside_a_git_work_tree_is_refused() -> None:
    with pytest.raises(
        LandError,
        match=r"^S-0001 cannot land: /src/project/.fgraph is not inside a git work tree$",
    ):
        land(READY, None)


def test_a_landing_on_a_record_git_ignores_takes_its_git_steps_but_the_commit_of_the_record() -> (
    None
):
    steps: list[object] = []
    land(READY, replace(work_tree(steps), ignores=lambda path: path == RECORD))
    assert steps == [
        ("merge", BRANCH),
        ("commit merge", MESSAGE),
        ("remove worktree", WORKTREE),
        ("delete branch", BRANCH),
    ]


def test_a_landing_on_a_record_git_ignores_completes_the_work_item_at_the_merge_commit() -> None:
    saved: list[WorkItemState] = []
    land(READY, replace(work_tree([]), ignores=lambda _: True), saved)
    assert [item.commit for item in saved if isinstance(item, CompletedWorkItem)] == [
        make_commit("3e9ae5c")
    ]


def test_a_landing_in_a_work_tree_that_is_not_on_main_is_refused() -> None:
    off_main = replace(work_tree([]), current_branch=lambda: BRANCH)
    with pytest.raises(LandError, match=rf"^S-0001 lands on main: /src/project is on {BRANCH}$"):
        land(READY, off_main)


def test_a_landing_without_a_branch_is_refused() -> None:
    with pytest.raises(LandError, match=r"^S-0001 has no branch wi/S-0001-\* to land$"):
        land(READY, replace(work_tree([]), find_branches=lambda _: []))


def test_a_landing_with_several_branches_is_refused_naming_them() -> None:
    two = replace(work_tree([]), find_branches=lambda _: [BRANCH, "wi/S-0001-other"])
    with pytest.raises(
        LandError, match=rf"^S-0001 has several branches to land: {BRANCH}, wi/S-0001-other$"
    ):
        land(READY, two)


def test_a_worktree_git_refuses_to_remove_says_the_work_item_is_landed() -> None:
    with pytest.raises(
        GitError,
        match=r"^git failed: refused -- S-0001 is landed at 3e9ae5c,"
        r" its worktree and its branch are not removed$",
    ):
        land(READY, replace(work_tree([]), remove_worktree=refuse))
