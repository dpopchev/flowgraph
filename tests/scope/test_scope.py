"""The scope of a branch: the work item it owns, and the store that saves that work item alone."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.commit import WorkTree
from flowgraph.criterion import make_scenario
from flowgraph.item import Store
from flowgraph.queue import Queue, make_queue
from flowgraph.scope import OutOfScopeError, Scope, scope_in, scope_of, within
from flowgraph.story import make_story, make_story_id
from flowgraph.upkeep import make_upkeep_id
from flowgraph.work_item import WorkItemState

pytestmark = pytest.mark.command

BRANCH = "wi/ST-0001-a-slug"
SCOPE = Scope(BRANCH, make_story_id(1))
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
SCENARIO = make_scenario("a", "b", "c")
OWN = make_story(make_story_id(1), "a title", SCENARIO, "", CREATED)
OTHER = make_story(make_story_id(2), "another title", SCENARIO, "", CREATED)


def never(*_: object) -> Never:
    """A read of the record, or a step of git, that the scope of a branch never asks for."""
    raise AssertionError("the scope guards the saves and asks git for the branch alone")


def store(saved: list[WorkItemState | Queue]) -> Store:
    """A store that notes what it saves."""
    return Store(
        find_work_item_rows=never,
        load_work_item=lambda _: OWN,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=saved.append,
        load_queue=never,
        save_queue=saved.append,
        find_changed_files=never,
        restore_files=never,
    )


def work_tree(branch: str) -> WorkTree:
    """A work tree on that branch."""
    return WorkTree(
        path=Path("/src/project"),
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: branch,
        find_branches=never,
        merge=never,
        abort_merge=never,
        commit_merge=never,
        find_worktree=never,
        remove_worktree=never,
        delete_branch=never,
    )


def test_the_branch_of_a_story_is_owned_by_that_story() -> None:
    assert scope_of(BRANCH) == SCOPE


def test_the_branch_of_an_upkeep_is_owned_by_that_upkeep() -> None:
    assert scope_of("wi/U-0002-cut-the-lines") == Scope(
        "wi/U-0002-cut-the-lines", make_upkeep_id(2)
    )


@pytest.mark.parametrize(
    "branch",
    ["main", "", "wi/ST-0001", "wi/XX-0001-a-slug", "feature/ST-0001-a-slug", "wi/T-0001-a-slug"],
    ids=["main", "no-branch", "no-slug", "no-kind", "no-wi-prefix", "a-task"],
)
def test_a_branch_named_otherwise_is_owned_by_no_work_item(branch: str) -> None:
    assert scope_of(branch) is None


def test_the_work_item_the_branch_owns_is_saved() -> None:
    saved: list[WorkItemState | Queue] = []
    within(store(saved), lambda: SCOPE, never).save_work_item(OWN)
    assert saved == [OWN]


def test_another_work_item_is_refused_naming_the_owner_of_the_branch() -> None:
    with pytest.raises(
        OutOfScopeError,
        match=rf"^ST-0002 is not written here: the branch {BRANCH} writes ST-0001 alone$",
    ):
        within(store([]), lambda: SCOPE, never).save_work_item(OTHER)


def test_another_work_item_refused_is_not_saved() -> None:
    saved: list[WorkItemState | Queue] = []
    with pytest.raises(OutOfScopeError):
        within(store(saved), lambda: SCOPE, never).save_work_item(OTHER)
    assert saved == []


def test_the_queue_is_refused_naming_the_owner_of_the_branch() -> None:
    with pytest.raises(
        OutOfScopeError,
        match=rf"^the Backlog is not reordered here: the branch {BRANCH} writes ST-0001 alone$",
    ):
        within(store([]), lambda: SCOPE, never).save_queue(make_queue([]))


def test_a_branch_no_work_item_owns_saves_every_work_item() -> None:
    saved: list[WorkItemState | Queue] = []
    within(store(saved), lambda: None, never).save_work_item(OTHER)
    assert saved == [OTHER]


def test_a_branch_no_work_item_owns_saves_the_queue() -> None:
    saved: list[WorkItemState | Queue] = []
    within(store(saved), lambda: None, never).save_queue(make_queue([]))
    assert saved == [make_queue([])]


def test_a_read_asks_for_no_scope() -> None:
    assert within(store([]), never, never).load_work_item(make_story_id(1)) == OWN


def test_the_scope_of_a_record_is_the_one_of_the_branch_its_work_tree_is_on() -> None:
    assert scope_in(Path("/src/project/.fgraph"), lambda _: work_tree(BRANCH)) == SCOPE


def test_a_record_outside_a_git_work_tree_has_no_scope() -> None:
    assert scope_in(Path("/src/project/.fgraph"), lambda _: None) is None
