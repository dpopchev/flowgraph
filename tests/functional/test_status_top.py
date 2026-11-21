"""The criterion of the top of status: `fgraph status` lists five items under one heading.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it.
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
SIX = range(1, 7)


def completed(number: int) -> list[list[str]]:
    """The commands that add the Story of that number with one Task and complete both."""
    story, task, commit = f"ST-{number:04}", f"T-{number:04}", f"abc123{number}"
    return [
        ["add", "story", f"title {number}", *CRITERION],
        ["add", "task", "a task title", "--parent", story, "--output", "an output"],
        ["start", story],
        ["start", task],
        ["complete", task, "--commit", commit],
        ["complete", story, "--commit", commit],
    ]


SIX_COMPLETED = [argv for number in SIX for argv in completed(number)]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, at: datetime) -> Outcome:
    """Run the command at that time in cwd, whose record is `.fgraph/`, on the files of it."""
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
    )
    return Outcome(status, "".join(out), "".join(err))


def after(cwd: Path, argvs: Sequence[Sequence[str]], last: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the one before, then the last; its outcome."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(last, cwd, START + timedelta(seconds=len(argvs)))


class TestSixStoriesCompleted:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return after(tmp_path, SIX_COMPLETED, ["status"])

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_status_lists_the_five_completed_last_then_one_more(self, listed: Outcome) -> None:
        assert listed.out == (
            "Backlog (0)\n"
            "InProgress (0)\n"
            "Completed (6)\n"
            "  ST-0006  title 6  abc1236\n"
            "  ST-0005  title 5  abc1235\n"
            "  ST-0004  title 4  abc1234\n"
            "  ST-0003  title 3  abc1233\n"
            "  ST-0002  title 2  abc1232\n"
            "  ... 1 more\n"
        )


def test_status_all_lists_every_one(tmp_path: Path) -> None:
    listed = after(tmp_path, SIX_COMPLETED, ["status", "--all"])
    assert listed.out.splitlines()[-1] == "  ST-0001  title 1  abc1231"
