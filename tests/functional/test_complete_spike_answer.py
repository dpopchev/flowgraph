"""The criterion of S-0095: a Spike is completed with the yes or no of its hypothesis.

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
ADD_SPIKE = [
    *("add", "spike", "a spike title"),
    *("--hypothesis", "Can one file per item hold the record?"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "Q-0001", "--output", "an output"]
STARTED = [ADD_SPIKE, ADD_TASK, ["start", "Q-0001"], ["start", "T-0001"]]
TASK_DONE = ["complete", "T-0001", "--commit", "abc1234"]
SPIKE_DONE = ["complete", "Q-0001", "--commit", "def5678", "--decision", "no: one file is too big"]
WITH_NO = [*SPIKE_DONE, "--answer", "no"]


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


class TestAStartedSpikeCompletedWithItsDecisionAndTheAnswerNo:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STARTED, TASK_DONE, WITH_NO)

    def test_complete_exits_with_zero(self, completed: Outcome) -> None:
        assert completed.status == 0

    def test_status_lists_it_under_completed(self, completed: Outcome, tmp_path: Path) -> None:
        assert fgraph(["status"], tmp_path).out.splitlines()[2:4] == [
            "completed (1)",
            "  Q-0001  def5678  a spike title",
        ]

    def test_show_lists_the_answer_beside_the_decision(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "Q-0001"], tmp_path).out.splitlines()[4:6] == [
            "  decision     no: one file is too big",
            "  answer       no",
        ]


def test_a_spike_completed_without_its_answer_is_refused_naming_it(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *STARTED, TASK_DONE, SPIKE_DONE)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: Q-0001 is completed with its answer: yes or no"],
    )
