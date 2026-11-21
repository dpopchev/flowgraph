"""The criterion of writing a Task: once added to a Story, `fgraph show` lists it inside it."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import Store, run
from flowgraph.queue import make_queue
from flowgraph.story import (
    StoryId,
    StoryNotFoundError,
    StoryState,
    story_detail,
    story_id_text,
    story_row,
)
from flowgraph.task import task_id_text

pytestmark = pytest.mark.functional

CWD = Path("/work")
NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], saved: dict[str, StoryState]) -> Outcome:
    """Run the command in CWD on a record whose stories are the ones saved so far, by id."""

    def held(story_id: StoryId) -> StoryState:
        if story_id_text(story_id) not in saved:
            raise StoryNotFoundError(story_id)
        return saved[story_id_text(story_id)]

    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        CWD,
        lambda path: path == CWD / ".fgraph",
        out.append,
        err.append,
        open_store=lambda _: Store(
            find_work_item_rows=lambda kind: [
                story_row(story) for story in saved.values() if story.id.kind == kind
            ],
            load_work_item=held,
            find_work_item_detail=lambda story_id: story_detail(held(story_id)),
            find_task_ids=lambda: [
                task_id_text(task.id) for story in saved.values() for task in story.tasks
            ],
            save_work_item=lambda story: saved.__setitem__(story_id_text(story.id), story),
            load_queue=lambda: make_queue([]),
            save_queue=lambda _: None,
            find_changed_files=lambda: [],
            restore_files=lambda: None,
        ),
        open_git=lambda _: None,
        now=lambda: NOW,
    )
    return Outcome(status, "".join(out), "".join(err))


class TestATaskAddedToAStoryInBacklog:
    @pytest.fixture
    def added(self) -> tuple[Outcome, Outcome]:
        """The outcome of adding a Task to the one Story of a record, then of showing the Story."""
        saved: dict[str, StoryState] = {}
        fgraph(ADD_STORY, saved)
        return fgraph(ADD_TASK, saved), fgraph(["show", "ST-0001"], saved)

    def test_add_exits_with_zero(self, added: tuple[Outcome, Outcome]) -> None:
        assert added[0].status == 0

    def test_add_names_the_task_and_its_story(self, added: tuple[Outcome, Outcome]) -> None:
        assert added[0].out == "added T-0001 to ST-0001\n"

    def test_show_lists_the_task_inside_the_story(self, added: tuple[Outcome, Outcome]) -> None:
        assert added[1].out == (
            "ST-0001  a title\n"
            "  bucket       Backlog\n"
            "  given        a state\n"
            "  when         an action\n"
            "  then         another\n"
            "Tasks (1)\n"
            "  T-0001  a task title\n"
            "    expected output  an output\n"
        )


def test_show_lists_the_descriptions_of_a_story_and_its_task() -> None:
    saved: dict[str, StoryState] = {}
    fgraph([*ADD_STORY, "--description", "why"], saved)
    fgraph([*ADD_TASK, "--description", "how"], saved)
    assert fgraph(["show", "ST-0001"], saved).out == (
        "ST-0001  a title\n"
        "  bucket       Backlog\n"
        "  description  why\n"
        "  given        a state\n"
        "  when         an action\n"
        "  then         another\n"
        "Tasks (1)\n"
        "  T-0001  a task title\n"
        "    expected output  an output\n"
        "    description      how\n"
    )


def changed(argv: Sequence[str], old: str, new: str) -> list[str]:
    """The arguments with one word replaced."""
    return [new if word == old else word for word in argv]


class TestATaskAddedToAStoryTheRecordDoesNotHold:
    @pytest.fixture
    def outcome(self) -> Outcome:
        saved: dict[str, StoryState] = {}
        fgraph(ADD_STORY, saved)
        return fgraph(changed(ADD_TASK, "ST-0001", "ST-0002"), saved)

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_story(self, outcome: Outcome) -> None:
        assert outcome.err.endswith("fgraph: error: no Story ST-0002 in the record\n")


class TestATaskAddedToAParentThatIsNoStory:
    @pytest.fixture
    def outcome(self) -> Outcome:
        return fgraph(changed(ADD_TASK, "ST-0001", "B-0001"), {})

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_parent(self, outcome: Outcome) -> None:
        assert outcome.err.endswith(
            "fgraph: error: 'B-0001' is no Story id: it is ST- and a number\n"
        )


class TestATaskAddedWithABlankOutput:
    @pytest.fixture
    def outcome(self) -> Outcome:
        saved: dict[str, StoryState] = {}
        fgraph(ADD_STORY, saved)
        return fgraph(changed(ADD_TASK, "an output", " "), saved)

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_blank_part(self, outcome: Outcome) -> None:
        assert outcome.err.endswith("fgraph: error: output is empty\n")


class TestAStoryShownThatTheRecordDoesNotHold:
    @pytest.fixture
    def outcome(self) -> Outcome:
        return fgraph(["show", "ST-0002"], {})

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_story(self, outcome: Outcome) -> None:
        assert outcome.err.endswith("fgraph: error: no Story ST-0002 in the record\n")


class TestAnIdShownThatIsNoStoryId:
    @pytest.fixture
    def outcome(self) -> Outcome:
        return fgraph(["show", "T-0001"], {})

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_id(self, outcome: Outcome) -> None:
        assert outcome.err.endswith(
            "fgraph: error: 'T-0001' is no Story id: it is ST- and a number\n"
        )
