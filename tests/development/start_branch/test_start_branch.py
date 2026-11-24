"""The start of a work item while its branch is there: what the check lets pass and what it names.

The start takes over no branch that is there, so it is refused before it writes. A work item with
no Task and one past Backlog are left to the start, which refuses them in its own words.
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.development import SlugError
from flowgraph.development.commit import OpenGit, WorkTree
from flowgraph.development.start_branch import BranchExistsError, check_branch_free
from flowgraph.record import Config, make_config
from flowgraph.record.store import Store
from flowgraph.story import make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItem,
    WorkItemState,
    append_task,
    make_work_item,
    started_work_item,
)

pytestmark = pytest.mark.command

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ON = make_config("[development]\nenabled = true\n")
OFF = make_config("")
TOP = Path("/src/project")
RECORD = TOP / ".fgraph"


def story(*, tasks: int = 1) -> WorkItem:
    """S-0002 titled a title in Backlog, with that many Tasks."""
    item = make_work_item(
        make_story_id(2),
        "a title",
        make_scenario("a state", "an action", "another"),
        "",
        CREATED,
    )
    for _ in range(tasks):
        item = append_task(item, make_task(make_task_id(1), "a task", "an output", "", CREATED))
    return item


def never(*_: object) -> Never:
    """A read or a git step that the check passes without."""
    raise AssertionError("the check reads nothing when there is nothing to check")


def storing(held: WorkItemState | None) -> Store:
    """A store that loads that work item whatever the id, none when it is to be never read."""
    return Store(
        find_work_item_rows=never,
        load_work_item=never if held is None else lambda _: held,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def tree(find_branches: Callable[[str], list[str]]) -> WorkTree:
    """A work tree at TOP that lists branches as given; the check asks for no other step."""
    return WorkTree(
        path=TOP,
        commit_files=never,
        add_worktree=never,
        current_branch=never,
        find_branches=find_branches,
        find_worktree=never,
        find_worktrees=never,
    )


def there(*branches: str) -> OpenGit:
    """The git of a work tree whose branches are those, answered by the name asked for."""
    return lambda _: tree(lambda name: [branch for branch in branches if branch == name])


def checked(
    item: str = "S-0002",
    *,
    held: WorkItemState | None = None,
    slug: str | None = None,
    open_git: OpenGit,
    config: Config = ON,
) -> None:
    """Run the check of that item, holding that work item (a Story with a Task by default)."""
    check_branch_free(
        item, slug, storing(story() if held is None else held), RECORD, open_git, config
    )


def test_a_story_whose_branch_is_there_is_refused_in_the_whole_line() -> None:
    with pytest.raises(BranchExistsError) as error:
        checked(open_git=there("wi/S-0002-a-title"))
    assert str(error.value) == (
        "S-0002 cannot start: the branch wi/S-0002-a-title is there already"
        " -- delete it or give another --slug"
    )


def test_a_story_started_under_a_slug_whose_branch_is_there_names_that_branch() -> None:
    with pytest.raises(
        BranchExistsError, match=r"^S-0002 cannot start: the branch wi/S-0002-a-slug is"
    ):
        checked(slug="a-slug", open_git=there("wi/S-0002-a-slug"))


def test_a_story_with_no_branch_there_passes() -> None:
    assert checked(open_git=there()) is None


def test_a_story_with_another_branch_there_passes() -> None:
    assert checked(open_git=there("wi/S-0002-other")) is None


def test_git_is_asked_for_the_exact_name_of_the_branch() -> None:
    asked: list[str] = []

    def find_branches(name: str) -> list[str]:
        asked.append(name)
        return []

    checked(open_git=lambda _: tree(find_branches))
    assert asked == ["wi/S-0002-a-title"]


def test_a_story_whose_slug_is_none_raises_the_slug_error() -> None:
    with pytest.raises(SlugError):
        checked(slug="Bad Slug", open_git=there())


def test_a_story_with_no_task_passes_while_its_branch_is_there() -> None:
    assert checked(held=story(tasks=0), open_git=there("wi/S-0002-a-title")) is None


def test_a_story_started_already_passes_while_its_branch_is_there() -> None:
    begun = started_work_item(story(), CREATED)
    assert checked(held=begun, open_git=there("wi/S-0002-a-title")) is None


@pytest.mark.parametrize("item", ["T-0001", "no-id"])
def test_a_text_that_is_no_story_passes_with_git_and_the_store_never(item: str) -> None:
    assert check_branch_free(item, None, storing(None), RECORD, never, ON) is None


def test_the_development_off_passes_with_git_and_the_store_never() -> None:
    assert check_branch_free("S-0002", None, storing(None), RECORD, never, OFF) is None


def test_a_record_outside_a_work_tree_passes_with_the_store_never() -> None:
    assert check_branch_free("S-0002", None, storing(None), RECORD, lambda _: None, ON) is None


def test_a_record_git_ignores_is_checked_as_any_other() -> None:
    ignoring = replace(tree(lambda name: [name]), ignores=lambda _: True)
    with pytest.raises(BranchExistsError):
        checked(open_git=lambda _: ignoring)
