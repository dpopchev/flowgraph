"""The criterion of the order of Completed: `fgraph status` lists the last completed first.

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

# What status lists once ST-0029 lands; what holds already has no mark.
NOT_YET = pytest.mark.xfail(strict=True, reason="ST-0029: Completed is listed by number yet")

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
ADD_OTHER_TASK = ["add", "task", "a task title", "--parent", "ST-0002", "--output", "an output"]
ADDED = [ADD_STORY, ADD_OTHER, ADD_TASK, ADD_OTHER_TASK]
COMPLETE_FIRST = [
    ["start", "ST-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "ST-0001", "--commit", "abc1234"],
]
COMPLETE_SECOND = [
    ["start", "ST-0002"],
    ["start", "T-0002"],
    ["complete", "T-0002", "--commit", "def5678"],
    ["complete", "ST-0002", "--commit", "def5678"],
]


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


class TestTwoStoriesCompletedTheSecondBeforeTheFirst:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return status_after(tmp_path, *ADDED, *COMPLETE_SECOND, *COMPLETE_FIRST)

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_status_lists_the_first_above_the_second_under_completed(self, listed: Outcome) -> None:
        assert listed.out == (
            "Backlog (0)\n"
            "InProgress (0)\n"
            "Completed (2)\n"
            "  ST-0001  a title  abc1234\n"
            "  ST-0002  another title  def5678\n"
        )


@NOT_YET
def test_the_second_story_completed_after_the_first_is_listed_above_it(tmp_path: Path) -> None:
    listed = status_after(tmp_path, *ADDED, *COMPLETE_FIRST, *COMPLETE_SECOND)
    assert listed.out.splitlines()[2:] == [
        "Completed (2)",
        "  ST-0002  another title  def5678",
        "  ST-0001  a title  abc1234",
    ]
