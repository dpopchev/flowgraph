"""The criterion of the order of InProgress: `fgraph status` lists the last started first.

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
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_OTHER_TASK = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
ADDED = [ADD_STORY, ADD_OTHER, ADD_TASK, ADD_OTHER_TASK]
START_FIRST = ["start", "S-0001"]
START_SECOND = ["start", "S-0002"]


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


def status_after(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the last, then `fgraph status`; its outcome."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(["status"], cwd, START + timedelta(seconds=len(argvs)))


class TestTwoStoriesStartedTheFirstBeforeTheSecond:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return status_after(tmp_path, *ADDED, START_FIRST, START_SECOND)

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_status_lists_the_second_above_the_first_under_in_progress(
        self, listed: Outcome
    ) -> None:
        assert listed.out == (
            "Backlog (0)\n"
            "InProgress (2)\n"
            "  S-0002  0/1 T  another title\n"
            "  S-0001  0/1 T  a title\n"
            "Completed (0)\n"
        )


def test_the_first_story_started_after_the_second_is_listed_above_it(tmp_path: Path) -> None:
    listed = status_after(tmp_path, *ADDED, START_SECOND, START_FIRST)
    assert listed.out.splitlines()[1:4] == [
        "InProgress (2)",
        "  S-0001  0/1 T  a title",
        "  S-0002  0/1 T  another title",
    ]
