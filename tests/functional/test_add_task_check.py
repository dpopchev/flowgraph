"""The criterion of the check of a Task: with the development on a Task is added with its command.

Run through `run` on a record whose stories are held in memory, as test_add_task.py does; the
configuration is the one the test hands it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import Store, run
from flowgraph.record import make_config
from flowgraph.record.queue import make_queue
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
ON = "[development]\nenabled = true\n"
OFF = ""
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], saved: dict[str, StoryState], config: str) -> Outcome:
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
        load_config=lambda _: make_config(config),
    )
    return Outcome(status, "".join(out), "".join(err))


@pytest.mark.xfail(strict=True, reason="S-0088 adds --check to fgraph add task")
class TestATaskAddedWithItsCheckWithTheDevelopmentOn:
    @pytest.fixture
    def added(self) -> tuple[Outcome, Outcome]:
        """The outcome of adding a Task with its check to a Story, then of showing the Story."""
        saved: dict[str, StoryState] = {}
        fgraph(ADD_STORY, saved, ON)
        return (
            fgraph([*ADD_TASK, "--check", "make test"], saved, ON),
            fgraph(["show", "S-0001"], saved, ON),
        )

    def test_add_exits_with_zero(self, added: tuple[Outcome, Outcome]) -> None:
        assert added[0].status == 0

    def test_show_lists_the_check_under_the_task(self, added: tuple[Outcome, Outcome]) -> None:
        assert "    check            make test\n" in added[1].out


@pytest.mark.xfail(strict=True, reason="S-0088 adds --check to fgraph add task")
class TestATaskAddedWithoutItsCheckWithTheDevelopmentOn:
    @pytest.fixture
    def outcome(self) -> Outcome:
        saved: dict[str, StoryState] = {}
        fgraph(ADD_STORY, saved, ON)
        return fgraph(ADD_TASK, saved, ON)

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_check(self, outcome: Outcome) -> None:
        assert "--check" in outcome.err.splitlines()[-1]


@pytest.mark.xfail(strict=True, reason="S-0088 adds --check to fgraph add task")
class TestATaskAddedWithItsCheckWithTheDevelopmentOff:
    @pytest.fixture
    def outcome(self) -> Outcome:
        saved: dict[str, StoryState] = {}
        fgraph(ADD_STORY, saved, OFF)
        return fgraph([*ADD_TASK, "--check", "make test"], saved, OFF)

    def test_exits_with_two(self, outcome: Outcome) -> None:
        assert outcome.status == 2

    def test_names_the_key_that_turns_the_development_on(self, outcome: Outcome) -> None:
        assert "development.enabled" in outcome.err.splitlines()[-1]
