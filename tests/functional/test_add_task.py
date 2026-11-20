"""The criterion of writing a Task: once added to a Story, `fgraph show` lists it inside it."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import run
from flowgraph.story import (
    Story,
    StoryId,
    StoryNotFoundError,
    story_detail,
    story_id_text,
    story_row,
    task_id_text,
)

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="ST-0001: fgraph add task and fgraph show are stubs"),
]

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


def fgraph(argv: Sequence[str], saved: dict[str, Story]) -> Outcome:
    """Run the command in CWD on a record whose stories are the ones saved so far, by id."""

    def held(story_id: StoryId) -> Story:
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
        read_story_rows=lambda _: [story_row(story) for story in saved.values()],
        read_story=lambda _, story_id: held(story_id),
        read_story_detail=lambda _, story_id: story_detail(held(story_id)),
        read_task_ids=lambda _: [
            task_id_text(task.id) for story in saved.values() for task in story.tasks
        ],
        write_story=lambda _, story: saved.__setitem__(story_id_text(story.id), story),
        now=lambda: NOW,
    )
    return Outcome(status, "".join(out), "".join(err))


class TestATaskAddedToAStoryInBacklog:
    @pytest.fixture
    def added(self) -> tuple[Outcome, Outcome]:
        """The outcome of adding a Task to the one Story of a record, then of showing the Story."""
        saved: dict[str, Story] = {}
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
