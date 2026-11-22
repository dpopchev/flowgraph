"""The criterion of the width of status: on a terminal `fgraph status` cuts a line to its width.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it, on a terminal of a width given.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
LONG = "a title that is much longer than a terminal of forty columns is wide"
ADD_STORY = ["add", "story", LONG, *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
COMPLETED = [
    ADD_STORY,
    ADD_TASK,
    ["start", "S-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "abc1234"],
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, at: datetime, width: int | None = None) -> Outcome:
    """Run the command at that time in cwd on the files of `.fgraph/`, on a terminal that wide.

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
        now=lambda: at,
        width=lambda: width,
    )
    return Outcome(status, "".join(out), "".join(err))


def status_after(cwd: Path, argvs: Sequence[Sequence[str]], width: int | None) -> Outcome:
    """Run each command in cwd a second after the last, then `fgraph status` on that width."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(["status"], cwd, START + timedelta(seconds=len(argvs)), width)


class TestAStoryWhoseLineIsLongerThanTheTerminal:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return status_after(tmp_path, [ADD_STORY], 40)

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_status_cuts_the_line_of_the_story_to_the_width_of_the_terminal(
        self, listed: Outcome
    ) -> None:
        assert listed.out == (
            "Backlog (1)\n> S-0001  a title that is much longer...\nInProgress (0)\nCompleted (0)\n"
        )


def test_status_written_to_no_terminal_lists_the_line_whole(tmp_path: Path) -> None:
    listed = status_after(tmp_path, [ADD_STORY], None)
    assert listed.out.splitlines()[1] == f"> S-0001  {LONG}"


def test_status_keeps_the_commit_of_a_completed_story_on_a_line_cut(tmp_path: Path) -> None:
    listed = status_after(tmp_path, COMPLETED, 40)
    assert listed.out.splitlines()[3] == "  S-0001  abc1234  a title that is mu..."
