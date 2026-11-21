"""The criterion of the started Task in status: `fgraph status` lists it under its work item.

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
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_OTHER_TASK = ["add", "task", "another task", "--parent", "S-0001", "--output", "an output"]
STARTED = [ADD_STORY, ADD_TASK, ADD_OTHER_TASK, ["start", "S-0001"], ["start", "T-0001"]]
BLOCK = ["block", "T-0001", "--reason", "a reason", "--waiting-on", "the reviewer"]


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


class TestAStoryStartedWithATaskOfItStarted:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return status_after(tmp_path, *STARTED)

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_status_lists_the_started_task_under_its_story(self, listed: Outcome) -> None:
        assert listed.out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  S-0001  0/2 T  a title\n"
            "    => T-0001  a task title\n"
            "Completed (0)\n"
        )


def test_a_blocked_task_is_listed_with_what_it_waits_on(tmp_path: Path) -> None:
    listed = status_after(tmp_path, *STARTED, BLOCK)
    assert listed.out.splitlines()[3] == "    !  T-0001  a task title  -- waiting on the reviewer"
