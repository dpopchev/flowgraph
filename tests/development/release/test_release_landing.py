"""The tag of a landing: the version the landing names, made before it completes, with fakes."""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.bug import BUG
from flowgraph.development import GitError
from flowgraph.development.commit import ReleaseSteps, WorkTree
from flowgraph.development.release import release_landing
from flowgraph.record import Config, make_config
from flowgraph.record.store import Store
from flowgraph.spike import SPIKE
from flowgraph.story import STORY
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import Kind, WorkItemRow

pytestmark = pytest.mark.command

OFF = make_config("")
PUSHED = make_config("[delivery]\npush = true\n")
TOP = Path("/src/project")
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
TAGGED = datetime(2026, 1, 5, tzinfo=UTC)
AFTER = datetime(2026, 1, 6, tzinfo=UTC)
HEAD = "4c2e1d0"
LANDED = "3e9ae5c"
TAG_MADE = ("tag", "v0.1.0", "release v0.1.0", "main")


def never(*_: object) -> Never:
    """A read, a write or a git step that the tag of a landing never asks for."""
    raise AssertionError("the tag of a landing reads the rows of the work items and the tags alone")


def refuse(*_: object) -> Never:
    """A git step that git refuses."""
    raise GitError("git failed: refused")


def row(item: str, commit: str) -> WorkItemRow:
    """A work item of the record as its row, completed after the tag."""
    return WorkItemRow(
        item, "a title", "completed", commit=commit, created=CREATED, completed=AFTER
    )


def store(rows: Mapping[str, Sequence[WorkItemRow]]) -> Store:
    """The store of a record holding the rows, by the prefix of their kind."""

    def find_work_item_rows(kind: Kind) -> list[WorkItemRow]:
        return list(rows.get(kind.prefix, ()))

    return Store(
        find_work_item_rows=find_work_item_rows,
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def work_tree(
    steps: list[object], tags: Sequence[str] = (), held: Collection[str] = ()
) -> WorkTree:
    """A work tree at TOP on main with the tags, the last of which holds the commits held.

    It notes each tag it makes and each tag it pushes.
    """

    def make_tag(tag: str, message: str, branch: str) -> str:
        steps.append(("tag", tag, message, branch))
        return HEAD

    def push_tag(branch: str, tag: str) -> str:
        steps.append(("push", branch, tag))
        return "origin"

    return WorkTree(
        path=TOP,
        commit_files=never,
        add_worktree=never,
        current_branch=lambda: "main",
        find_branches=never,
        find_worktree=never,
        find_worktrees=never,
        release=ReleaseSteps(
            find_tags=lambda _: list(tags),
            holds_commit=lambda _, commit: commit in held,
            tagged_at=lambda _: TAGGED,
            make_tag=make_tag,
            push_tag=push_tag,
        ),
    )


def landed(
    kind: Kind,
    tree: WorkTree,
    rows: Mapping[str, Sequence[WorkItemRow]] | None = None,
    config: Config = OFF,
) -> str:
    """The lines of the tag of the landing of a work item of that kind, at the commit LANDED."""
    return release_landing(kind, LANDED, store(rows or {}), tree.release, config)


def test_a_story_landed_with_no_tag_makes_the_first_one_on_main() -> None:
    steps: list[object] = []
    landed(STORY, work_tree(steps))
    assert steps == [TAG_MADE]


def test_it_says_the_tag_at_the_commit_the_tag_is_made_on() -> None:
    assert landed(STORY, work_tree([])) == f"tagged v0.1.0 at {HEAD}\n"


@pytest.mark.parametrize(
    ("kind", "expected"),
    [(STORY, "v0.2.0"), (BUG, "v0.2.0"), (UPKEEP, "v0.1.1"), (SPIKE, "v0.1.1")],
    ids=["a-story", "a-bug", "an-upkeep", "a-spike"],
)
def test_the_kind_of_the_work_item_landed_names_the_number_after_the_last_tag(
    kind: Kind, expected: str
) -> None:
    steps: list[object] = []
    landed(kind, work_tree(steps, ["v0.1.0"]))
    assert steps == [("tag", expected, f"release {expected}", "main")]


def test_an_upkeep_landed_with_a_story_completed_since_the_last_tag_names_the_next_minor() -> None:
    steps: list[object] = []
    landed(UPKEEP, work_tree(steps, ["v0.1.0"]), {"S": [row("S-0001", "c0000a1")]})
    assert steps == [("tag", "v0.2.0", "release v0.2.0", "main")]


def test_a_story_the_last_tag_holds_is_not_counted_since_it() -> None:
    steps: list[object] = []
    tree = work_tree(steps, ["v0.1.0"], held={"c0000a1"})
    landed(UPKEEP, tree, {"S": [row("S-0001", "c0000a1")]})
    assert steps == [("tag", "v0.1.1", "release v0.1.1", "main")]


def test_a_landing_whose_commit_the_last_tag_holds_makes_no_tag() -> None:
    steps: list[object] = []
    said = landed(STORY, work_tree(steps, ["v0.1.0"], held={LANDED}))
    assert (steps, said) == ([], f"tagged v0.1.0 at {LANDED}\n")


def test_a_landing_taken_up_names_the_tag_that_holds_its_commit_at_that_commit() -> None:
    assert landed(UPKEEP, work_tree([], ["v0.1.0"], held={LANDED})) == (
        f"tagged v0.1.0 at {LANDED}\n"
    )


class TestALandingWithThePushOfTheDeliveryOn:
    @pytest.fixture
    def steps(self) -> list[object]:
        return []

    @pytest.fixture
    def said(self, steps: list[object]) -> str:
        return landed(STORY, work_tree(steps), config=PUSHED)

    def test_the_tag_is_pushed_once_it_is_made(self, said: str, steps: list[object]) -> None:
        assert steps == [TAG_MADE, ("push", "main", "v0.1.0")]

    def test_it_names_the_remote_the_tag_is_pushed_to(self, said: str) -> None:
        assert said == f"tagged v0.1.0 at {HEAD}\npushed v0.1.0 to origin\n"


def test_a_tag_taken_up_is_pushed_again() -> None:
    steps: list[object] = []
    said = landed(STORY, work_tree(steps, ["v0.1.0"], held={LANDED}), config=PUSHED)
    assert (steps, said) == (
        [("push", "main", "v0.1.0")],
        f"tagged v0.1.0 at {LANDED}\npushed v0.1.0 to origin\n",
    )


def test_a_tag_git_refuses_says_main_is_not_tagged() -> None:
    tree = work_tree([])
    refused = replace(tree, release=replace(tree.release, make_tag=refuse))
    with pytest.raises(GitError) as error:
        landed(STORY, refused)
    assert str(error.value) == "git failed: refused -- main is not tagged v0.1.0"


def test_a_push_of_the_tag_git_refuses_says_the_tag_is_made_and_not_pushed() -> None:
    tree = work_tree([])
    refused = replace(tree, release=replace(tree.release, push_tag=refuse))
    with pytest.raises(GitError) as error:
        landed(STORY, refused, config=PUSHED)
    assert (
        str(error.value) == f"git failed: refused -- v0.1.0 is tagged at {HEAD}, it is not pushed"
    )
