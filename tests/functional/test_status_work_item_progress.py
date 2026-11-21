"""The criterion of the progress of a work item: `fgraph status` lists its Tasks completed.

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

NOT_YET = pytest.mark.xfail(
    strict=True, reason="ST-0033: a started work item is listed with no progress yet"
)

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
ONE_OF_THREE = [
    ADD_STORY,
    ADD_TASK,
    ADD_TASK,
    ADD_TASK,
    ["start", "ST-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
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


class TestAStoryStartedWithOneOfItsThreeTasksCompleted:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return status_after(tmp_path, *ONE_OF_THREE)

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    @NOT_YET
    def test_status_lists_the_story_with_its_tasks_completed_of_all(self, listed: Outcome) -> None:
        assert listed.out == (
            "Backlog (0)\nInProgress (1)\n  ST-0001  1/3 T  a title\nCompleted (0)\n"
        )


@NOT_YET
def test_a_started_task_is_not_counted_as_completed(tmp_path: Path) -> None:
    listed = status_after(tmp_path, *ONE_OF_THREE, ["start", "T-0002"])
    assert listed.out.splitlines()[2] == "  ST-0001  1/3 T  a title"
