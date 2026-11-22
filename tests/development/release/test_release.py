"""The release of the trunk: the version it tags, what it refuses and its push, with fakes."""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.development import GitError
from flowgraph.development.commit import ReleaseSteps, Said, WorkTree
from flowgraph.development.release import ReleaseError, release_trunk
from flowgraph.development.scope import NotOnMainError
from flowgraph.development.version import VersionError
from flowgraph.record import Config, make_config
from flowgraph.record.store import Store
from flowgraph.work_item import Kind, WorkItemRow

pytestmark = pytest.mark.command

OFF = make_config("")
PUSHED = make_config("[delivery]\npush = true\n")
TOP = Path("/src/project")
RECORD = TOP / ".fgraph"
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
TAGGED = datetime(2026, 1, 5, tzinfo=UTC)
BEFORE = datetime(2026, 1, 4, tzinfo=UTC)
AFTER = datetime(2026, 1, 6, tzinfo=UTC)
HEAD = "4c2e1d0"


def never(*_: object) -> Never:
    """A read, a write or a git step that a release never asks for."""
    raise AssertionError("a release reads the rows of the work items and the tags alone")


def refuse(*_: object) -> Never:
    """A git step that git refuses."""
    raise GitError("git failed: refused")


def row(
    item: str, commit: str = "", completed: datetime = AFTER, state: str = "completed"
) -> WorkItemRow:
    """A work item of the record as its row: completed by default, after the tag."""
    return WorkItemRow(item, "a title", state, commit=commit, created=CREATED, completed=completed)


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
            holds_commit=lambda _, commit: (commit in held) if commit.startswith("c") else None,
            tagged_at=lambda _: TAGGED,
            make_tag=make_tag,
            push_tag=push_tag,
        ),
    )


def released(
    rows: Mapping[str, Sequence[WorkItemRow]],
    tree: WorkTree,
    asked: str | None = None,
    config: Config = OFF,
) -> Said:
    """Release the trunk of the record holding the rows in the work tree."""
    return release_trunk(asked, store(rows), RECORD, lambda _: tree, config)


class TestAStoryCompletedSinceTheLastTag:
    @pytest.fixture
    def steps(self) -> list[object]:
        steps: list[object] = []
        released({"S": [row("S-0001", "c0000a1")]}, work_tree(steps, ["v0.1.0"]))
        return steps

    def test_the_next_minor_is_tagged_on_main_with_its_message(self, steps: list[object]) -> None:
        assert steps == [("tag", "v0.2.0", "release v0.2.0", "main")]


def test_a_release_names_the_tag_and_the_commit_it_is_on() -> None:
    said = released({"S": [row("S-0001", "c0000a1")]}, work_tree([], ["v0.1.0"]))
    assert said == Said(f"tagged v0.2.0 at {HEAD}\n")


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ({"B": [row("B-0001", "c0000a1")]}, "v0.2.0"),
        ({"U": [row("U-0001", "c0000a1")]}, "v0.1.1"),
        ({"Q": [row("Q-0001", "c0000a1")]}, "v0.1.1"),
        ({"U": [row("U-0001", "c0000a1")], "S": [row("S-0001", "c0000b2")]}, "v0.2.0"),
    ],
    ids=["a-bug", "an-upkeep", "a-spike", "an-upkeep-and-a-story"],
)
def test_the_kinds_completed_since_the_last_tag_name_its_number(
    rows: Mapping[str, Sequence[WorkItemRow]], expected: str
) -> None:
    steps: list[object] = []
    released(rows, work_tree(steps, ["v0.1.0"]))
    assert steps == [("tag", expected, f"release {expected}", "main")]


def test_a_story_whose_commit_the_last_tag_holds_is_released_already() -> None:
    steps: list[object] = []
    rows = {"S": [row("S-0001", "c0000a1")], "U": [row("U-0001", "c0000b2")]}
    released(rows, work_tree(steps, ["v0.1.0"], held={"c0000a1"}))
    assert steps == [("tag", "v0.1.1", "release v0.1.1", "main")]


def test_the_last_tag_is_the_highest_version_among_the_tags() -> None:
    steps: list[object] = []
    tags = ["v0.9.0", "v0.10.0", "latest"]
    released({"U": [row("U-0001", "c0000a1")]}, work_tree(steps, tags))
    assert steps == [("tag", "v0.10.1", "release v0.10.1", "main")]


def test_a_first_release_without_a_tag_is_v0_1_0() -> None:
    steps: list[object] = []
    released({"S": [row("S-0001", "c0000a1")]}, work_tree(steps))
    assert steps == [("tag", "v0.1.0", "release v0.1.0", "main")]


def test_a_story_without_a_commit_completed_after_the_tag_is_completed_since() -> None:
    steps: list[object] = []
    released({"S": [row("S-0001", completed=AFTER)]}, work_tree(steps, ["v0.1.0"]))
    assert steps == [("tag", "v0.2.0", "release v0.2.0", "main")]


def test_a_story_without_a_commit_completed_before_the_tag_is_released_already() -> None:
    rows = {"S": [row("S-0001", completed=BEFORE)]}
    with pytest.raises(ReleaseError, match=r"^nothing is completed since v0\.1\.0: no release"):
        released(rows, work_tree([], ["v0.1.0"]))


def test_a_story_whose_commit_git_does_not_know_is_taken_by_its_time() -> None:
    rows = {"S": [row("S-0001", "abc1234", completed=BEFORE)]}
    with pytest.raises(ReleaseError, match=r"^nothing is completed since v0\.1\.0: no release"):
        released(rows, work_tree([], ["v0.1.0"]))


@pytest.mark.parametrize("state", ["backlog", "started", "removed"])
def test_a_work_item_that_is_not_completed_is_not_released(state: str) -> None:
    rows = {"S": [row("S-0001", "c0000a1", state=state)]}
    with pytest.raises(ReleaseError, match=r"^nothing is completed since v0\.1\.0: no release"):
        released(rows, work_tree([], ["v0.1.0"]))


class TestNothingCompletedSinceTheLastTag:
    @pytest.fixture
    def steps(self) -> list[object]:
        return []

    @pytest.fixture
    def refused(self, steps: list[object]) -> ReleaseError:
        rows = {"S": [row("S-0001", "c0000a1")]}
        with pytest.raises(ReleaseError) as raised:
            released(rows, work_tree(steps, ["v0.1.0"], held={"c0000a1"}))
        return raised.value

    def test_it_is_refused_naming_the_last_tag(self, refused: ReleaseError) -> None:
        assert str(refused) == (
            "nothing is completed since v0.1.0: no release -- complete a work item first"
        )

    def test_no_tag_is_made(self, refused: ReleaseError, steps: list[object]) -> None:
        assert steps == []


def test_a_record_with_nothing_completed_and_no_tag_is_refused() -> None:
    with pytest.raises(
        ReleaseError, match=r"^nothing is completed: no release -- complete a work item first$"
    ):
        released({}, work_tree([]))


def test_the_version_asked_for_is_tagged() -> None:
    steps: list[object] = []
    released({"U": [row("U-0001", "c0000a1")]}, work_tree(steps, ["v0.1.0"]), "v1.0.0")
    assert steps == [("tag", "v1.0.0", "release v1.0.0", "main")]


def test_a_version_asked_for_that_is_tagged_already_is_refused() -> None:
    with pytest.raises(
        ReleaseError, match=r"^v0\.1\.0 is tagged already: a tag is never moved or deleted"
    ):
        released({"S": [row("S-0001", "c0000a1")]}, work_tree([], ["v0.1.0"]), "v0.1.0")


def test_a_version_asked_for_that_is_no_version_is_refused() -> None:
    with pytest.raises(VersionError, match=r"^'1\.0' is no version"):
        released({"S": [row("S-0001", "c0000a1")]}, work_tree([], ["v0.1.0"]), "1.0")


def test_a_version_asked_for_with_nothing_completed_since_is_refused() -> None:
    with pytest.raises(ReleaseError, match=r"^nothing is completed since v0\.1\.0: no release"):
        released({}, work_tree([], ["v0.1.0"]), "v1.0.0")


def test_a_release_outside_a_git_work_tree_is_refused_naming_the_record() -> None:
    with pytest.raises(
        ReleaseError, match=rf"^fgraph release tags main: {RECORD} is not inside a git work tree$"
    ):
        release_trunk(None, store({}), RECORD, lambda _: None, OFF)


def test_a_release_off_the_checkout_of_main_is_refused_as_a_start_is() -> None:
    tree = replace(
        work_tree([], ["v0.1.0"]),
        path=Path("/src/project.worktrees/S-0001-a-slug"),
        current_branch=lambda: "wi/S-0001-a-slug",
        find_worktree=lambda _: TOP,
    )
    with pytest.raises(
        NotOnMainError,
        match=(
            r"^fgraph release runs on main, in /src/project: "
            r"/src/project\.worktrees/S-0001-a-slug is on wi/S-0001-a-slug$"
        ),
    ):
        released({"S": [row("S-0001", "c0000a1")]}, tree)


class TestAReleaseWithThePushOfTheDeliveryOn:
    @pytest.fixture
    def steps(self) -> list[object]:
        return []

    @pytest.fixture
    def said(self, steps: list[object]) -> Said:
        return released(
            {"S": [row("S-0001", "c0000a1")]}, work_tree(steps, ["v0.1.0"]), None, PUSHED
        )

    def test_the_tag_is_pushed_once_it_is_made(self, said: Said, steps: list[object]) -> None:
        assert steps == [("tag", "v0.2.0", "release v0.2.0", "main"), ("push", "main", "v0.2.0")]

    def test_it_names_the_remote_the_tag_is_pushed_to(self, said: Said) -> None:
        assert said == Said(f"tagged v0.2.0 at {HEAD}\npushed v0.2.0 to origin\n")


def test_a_push_refused_says_the_tag_is_made_and_not_pushed() -> None:
    tree = work_tree([], ["v0.1.0"])
    tree = replace(tree, release=replace(tree.release, push_tag=refuse))
    with pytest.raises(
        GitError, match=rf"^git failed: refused -- v0\.2\.0 is tagged at {HEAD}, it is not pushed$"
    ):
        released({"S": [row("S-0001", "c0000a1")]}, tree, None, PUSHED)
