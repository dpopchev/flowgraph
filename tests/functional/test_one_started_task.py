"""The criterion of one started Task: a second Task of a Story is not started beside the first.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

# What a second start is refused for once ST-0013 lands; what still starts has no mark.
NOT_YET = pytest.mark.xfail(strict=True, reason="ST-0013: a work item starts any number of Tasks")

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
BLOCK = ["block", "T-0001", "--reason", "a reason", "--waiting-on", "someone"]
ONE_STARTED = (ADD_STORY, ADD_TASK, ADD_TASK, ["start", "ST-0001"], ["start", "T-0001"])
FIRST = "T-0001 is started -- complete or block it first"


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


@NOT_YET
class TestASecondTaskStartedBesideAStartedOne:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *ONE_STARTED, ["start", "T-0002"])

    def test_start_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_start_names_the_started_task(self, refused: Outcome) -> None:
        assert refused.err.splitlines()[-1:] == [f"fgraph: error: T-0002 cannot start: {FIRST}"]

    def test_the_second_task_stays_in_backlog(self, refused: Outcome, tmp_path: Path) -> None:
        assert fgraph(["show", "ST-0001"], tmp_path).out.splitlines()[-2:] == [
            "  T-0002  a task title",
            "    expected output  an output",
        ]


@NOT_YET
def test_a_task_unblocked_beside_a_started_one_is_refused_naming_it(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *ONE_STARTED, BLOCK, ["start", "T-0002"], ["unblock", "T-0001"])
    second = "T-0002 is started -- complete or block it first"
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        [f"fgraph: error: T-0001 cannot be unblocked: {second}"],
    )


def test_a_second_task_is_started_once_the_first_is_blocked(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *ONE_STARTED, BLOCK, ["start", "T-0002"])
    assert (outcome.status, outcome.out) == (0, "started T-0002 of ST-0001\n")


def test_a_second_task_is_started_once_the_first_is_completed(tmp_path: Path) -> None:
    done = ["complete", "T-0001", "--commit", "3e9ae5c"]
    outcome = runs(tmp_path, *ONE_STARTED, done, ["start", "T-0002"])
    assert (outcome.status, outcome.out) == (0, "started T-0002 of ST-0001\n")


def test_a_task_started_already_says_so_itself(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *ONE_STARTED, ["start", "T-0001"])
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: T-0001 is started already"],
    )
