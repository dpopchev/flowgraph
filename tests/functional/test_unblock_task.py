"""The criterion of unblocking a Task: `fgraph show` lists it started again, and it completes.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
START_STORY = ["start", "S-0001"]
START_TASK = ["start", "T-0001"]
BLOCK = ["block", "T-0001", "--reason", "the review is not back", "--waiting-on", "the reviewer"]
UNBLOCK = ["unblock", "T-0001"]
COMPLETE = ["complete", "T-0001", "--commit", "3e9ae5c"]
STARTED = (ADD_STORY, ADD_TASK, START_STORY, START_TASK)
BLOCKED = (*STARTED, BLOCK)


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
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
    )
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


class TestABlockedTaskUnblocked:
    @pytest.fixture
    def unblocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *BLOCKED, UNBLOCK)

    def test_unblock_exits_with_zero(self, unblocked: Outcome) -> None:
        assert unblocked.status == 0

    def test_unblock_names_the_task_and_its_story(self, unblocked: Outcome) -> None:
        assert unblocked.out == "unblocked T-0001 of S-0001\n"

    def test_show_lists_it_started_again(self, unblocked: Outcome, tmp_path: Path) -> None:
        assert fgraph(["show", "S-0001"], tmp_path).out.splitlines()[-3:] == [
            "  T-0001  a task title",
            "    bucket           in-progress",
            "    expected output  an output",
        ]

    def test_it_can_be_completed(self, unblocked: Outcome, tmp_path: Path) -> None:
        outcome = fgraph(COMPLETE, tmp_path)
        assert (outcome.status, outcome.out) == (0, "completed T-0001 of S-0001 at 3e9ae5c\n")

    def test_it_can_be_blocked_once_more(self, unblocked: Outcome, tmp_path: Path) -> None:
        assert fgraph(BLOCK, tmp_path).out == "blocked T-0001 of S-0001\n"


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_STORY, ADD_TASK, START_STORY, UNBLOCK], "T-0001 is not blocked"),
        ([*STARTED, UNBLOCK], "T-0001 is not blocked"),
        ([*STARTED, COMPLETE, UNBLOCK], "T-0001 is not blocked"),
        ([*BLOCKED, UNBLOCK, UNBLOCK], "T-0001 is not blocked"),
        ([*BLOCKED, ["unblock", "S-0001"]], "S-0001 is not blocked"),
        ([*BLOCKED, ["unblock", "T-0009"]], "no Task T-0009 in the record"),
    ],
    ids=[
        "task-in-backlog",
        "task-started",
        "task-completed",
        "unblocked-already",
        "a-work-item-id",
        "no-such-task",
    ],
)
def test_an_unblock_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])
