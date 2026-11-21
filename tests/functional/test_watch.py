"""The criterion of watch: `fgraph watch` writes what `fgraph status` writes again and again, so a
Story started between two frames is listed under InProgress in the next.

Run end to end on a record in a temporary directory, through the file adapters of the package.
The wait between two frames is a fake that starts the Story, so no test sleeps.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="ST-0038: fgraph has no watch command yet"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
IN_BACKLOG = "Backlog (1)\n  ST-0001  a title\nInProgress (0)\nCompleted (0)\n"
IN_PROGRESS = "Backlog (0)\nInProgress (1)\n  ST-0001  0/1 T  a title\nCompleted (0)\n"

# Wait that many seconds before the next frame.
Wait = Callable[[float], object]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def no_wait(_: float) -> None:
    """The wait of a command that writes no second frame."""


def fgraph(argv: Sequence[str], cwd: Path, wait: Wait = no_wait) -> Outcome:
    """Run the command in cwd on the files of `.fgraph/`, waiting between two frames by wait."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: NOW,
        wait=wait,  # pyright: ignore[reportCallIssue] -- until ST-0038 adds it
    )
    return Outcome(status, "".join(out), "".join(err))


class TestAStoryInBacklogStartedBetweenTwoFrames:
    @pytest.fixture
    def watched(self, tmp_path: Path) -> Outcome:
        for argv in (ADD_STORY, ADD_TASK):
            fgraph(argv, tmp_path)
        return fgraph(
            ["watch", "--count", "2"],
            tmp_path,
            wait=lambda _: fgraph(["start", "ST-0001"], tmp_path),
        )

    def test_watch_exits_with_zero(self, watched: Outcome) -> None:
        assert watched.status == 0

    def test_the_first_frame_lists_the_story_under_backlog(self, watched: Outcome) -> None:
        assert watched.out.startswith(IN_BACKLOG)

    def test_the_next_frame_lists_the_story_under_in_progress(self, watched: Outcome) -> None:
        assert watched.out.removeprefix(IN_BACKLOG) == IN_PROGRESS
