"""The criterion of adding a Story: once added, `fgraph status` lists it under Backlog."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import run
from flowgraph.story import Story, story_row

pytestmark = pytest.mark.functional

CWD = Path("/work")
NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD = ["add", "story", "a title", "--given", "a state", "--when", "an action", "--then", "another"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], saved: list[Story]) -> Outcome:
    """Run the command in CWD on a record whose stories are the ones saved so far."""
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        CWD,
        lambda path: path == CWD / ".fgraph",
        out.append,
        err.append,
        read_story_rows=lambda _: [story_row(story) for story in saved],
        write_story=lambda _, story: saved.append(story),
        now=lambda: NOW,
    )
    return Outcome(status, "".join(out), "".join(err))


@pytest.mark.xfail(strict=True, reason="the add-story Story: red until its last Task")
class TestAStoryAddedToARecordWithNoItems:
    @pytest.fixture
    def added(self) -> tuple[Outcome, Outcome]:
        """The outcome of the add, then of the status after it."""
        saved: list[Story] = []
        return fgraph(ADD, saved), fgraph(["status"], saved)

    def test_add_exits_with_zero(self, added: tuple[Outcome, Outcome]) -> None:
        assert added[0].status == 0

    def test_add_names_the_new_id(self, added: tuple[Outcome, Outcome]) -> None:
        assert added[0].out == "added ST-0001\n"

    def test_status_lists_it_under_backlog(self, added: tuple[Outcome, Outcome]) -> None:
        assert added[1].out == (
            "Backlog (1)\n  ST-0001  a title\nInProgress (0)\nCompleted (0)\n"
        )
