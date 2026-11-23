"""The criterion of blocking a Task: `fgraph show` lists it in InProgress as blocked.

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
STARTED = (ADD_STORY, ADD_TASK, START_STORY, START_TASK)


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


class TestAStartedTaskBlockedWithAReasonAndWhatItWaitsOn:
    @pytest.fixture
    def blocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STARTED, BLOCK)

    def test_block_exits_with_zero(self, blocked: Outcome) -> None:
        assert blocked.status == 0

    def test_block_names_the_task_and_its_story(self, blocked: Outcome) -> None:
        assert blocked.out == "blocked T-0001 of S-0001\n"

    def test_show_lists_it_in_inprogress_as_blocked_with_its_reason_and_what_it_waits_on(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], tmp_path).out == (
            "S-0001  a title\n"
            "  bucket       InProgress\n"
            "  given        a state\n"
            "  when         an action\n"
            "  then         another\n"
            "Tasks (1)\n"
            "  T-0001  a task title\n"
            "    bucket           InProgress, blocked\n"
            "    reason           the review is not back\n"
            "    waiting on       the reviewer\n"
            "    expected output  an output\n"
        )

    def test_status_still_lists_its_story_under_inprogress(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  S-0001  0/1 T  a title\n"
            "    !  T-0001  a task title  -- waiting on the reviewer: the review is not back\n"
            "Completed (0)\n"
        )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_STORY, ADD_TASK, START_STORY, BLOCK], "T-0001 is in Backlog: start it first"),
        ([*STARTED, BLOCK, BLOCK], "T-0001 is blocked already"),
        (
            [*STARTED, ["complete", "T-0001", "--commit", "3e9ae5c"], BLOCK],
            "T-0001 is completed already",
        ),
        (
            [*STARTED, ["block", "T-0001", "--reason", " ", "--waiting-on", "the reviewer"]],
            "reason is empty",
        ),
        (
            [*STARTED, ["block", "T-0001", "--reason", "a reason", "--waiting-on", ""]],
            "waiting on is empty",
        ),
        (
            [*STARTED, ["block", "T-0009", "--reason", "a reason", "--waiting-on", "someone"]],
            "no Task T-0009 in the record",
        ),
        (
            [*STARTED, BLOCK, ["complete", "T-0001", "--commit", "3e9ae5c"]],
            "T-0001 is blocked: unblock it first",
        ),
        ([*STARTED, BLOCK, START_TASK], "T-0001 is blocked: unblock it first"),
        (
            [*STARTED, BLOCK, ["complete", "S-0001", "--commit", "3e9ae5c"]],
            "S-0001 has Tasks to complete first: T-0001",
        ),
    ],
    ids=[
        "task-in-backlog",
        "blocked-already",
        "completed-already",
        "blank-reason",
        "blank-waiting-on",
        "no-such-task",
        "complete-a-blocked-task",
        "start-a-blocked-task",
        "complete-the-story-of-a-blocked-task",
    ],
)
def test_a_block_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])
