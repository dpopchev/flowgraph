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

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
LONG = "a title that is much longer than a terminal of forty columns is wide"
IN_BACKLOG = "Backlog (1)\n  ST-0001  a title\nInProgress (0)\nCompleted (0)\n"
IN_PROGRESS = "Backlog (0)\nInProgress (1)\n  ST-0001  0/1 T  a title\nCompleted (0)\n"

# What a terminal reads as: put the cursor home and clear the screen.
CLEAR = "\x1b[H\x1b[2J"

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


def interrupt(_: float) -> None:
    """The wait the developer ends with Ctrl-C."""
    raise KeyboardInterrupt


def fgraph(
    argv: Sequence[str], cwd: Path, wait: Wait = no_wait, width: int | None = None
) -> Outcome:
    """Run the command in cwd on the files of `.fgraph/`, waiting between two frames by wait.

    Without a width the output is no terminal.
    """
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
        wait=wait,
        width=lambda: width,
    )
    return Outcome(status, "".join(out), "".join(err))


@pytest.fixture
def six_in_backlog(tmp_path: Path) -> Path:
    """The directory of a record with six Stories in Backlog, one above the top status lists."""
    for _ in range(6):
        fgraph(ADD_STORY, tmp_path)
    return tmp_path


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


def test_watch_waits_five_seconds_between_two_frames(tmp_path: Path) -> None:
    waits: list[float] = []
    fgraph(["watch", "--count", "3"], tmp_path, wait=waits.append)
    assert waits == [5, 5]


def test_watch_waits_the_seconds_given_with_n(tmp_path: Path) -> None:
    waits: list[float] = []
    fgraph(["watch", "-n", "0.5", "--count", "2"], tmp_path, wait=waits.append)
    assert waits == [0.5]


def test_ctrl_c_ends_watch_with_zero_after_the_frame_written(tmp_path: Path) -> None:
    fgraph(ADD_STORY, tmp_path)
    assert fgraph(["watch"], tmp_path, wait=interrupt) == Outcome(0, IN_BACKLOG, "")


def test_on_a_terminal_a_frame_replaces_the_one_before_it(tmp_path: Path) -> None:
    fgraph(ADD_STORY, tmp_path)
    watched = fgraph(["watch", "--count", "2"], tmp_path, width=80)
    assert watched.out == f"{CLEAR}{IN_BACKLOG}{CLEAR}{IN_BACKLOG}"


def test_on_a_terminal_watch_cuts_a_line_to_its_width(tmp_path: Path) -> None:
    fgraph(["add", "story", LONG, *CRITERION], tmp_path)
    watched = fgraph(["watch", "--count", "1"], tmp_path, width=40)
    assert watched.out.splitlines()[1] == "  ST-0001  a title that is much longe..."


def test_watch_written_to_no_terminal_lists_a_line_whole(tmp_path: Path) -> None:
    fgraph(["add", "story", LONG, *CRITERION], tmp_path)
    watched = fgraph(["watch", "--count", "1"], tmp_path)
    assert watched.out.splitlines()[1] == f"  ST-0001  {LONG}"


def test_watch_lists_the_top_five_under_a_heading(six_in_backlog: Path) -> None:
    watched = fgraph(["watch", "--count", "1"], six_in_backlog)
    assert watched.out.splitlines()[5:7] == ["  ST-0005  a title", "  ... 1 more"]


def test_watch_all_lists_every_item(six_in_backlog: Path) -> None:
    watched = fgraph(["watch", "--all", "--count", "1"], six_in_backlog)
    assert watched.out.splitlines()[5:7] == ["  ST-0005  a title", "  ST-0006  a title"]


@pytest.mark.parametrize(
    ("argv", "error"),
    [
        (["watch", "-n", "0"], "-n 0 is no positive number of seconds"),
        (["watch", "-n", "-2"], "-n -2 is no positive number of seconds"),
        (["watch", "--count", "0"], "--count 0 is no positive number of frames"),
        (["watch", "--count", "-1"], "--count -1 is no positive number of frames"),
    ],
    ids=["no-seconds", "seconds-below-zero", "no-frame", "frames-below-zero"],
)
def test_a_watch_refused_exits_with_two_and_names_why(
    argv: list[str], error: str, tmp_path: Path
) -> None:
    outcome = fgraph(argv, tmp_path)
    assert (outcome.status, outcome.out, outcome.err.splitlines()[-1:]) == (
        2,
        "",
        [f"fgraph: error: {error}"],
    )
