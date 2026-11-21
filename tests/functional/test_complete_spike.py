"""The criterion of completing a Spike: `fgraph show` prints the decision under its hypothesis.

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
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_SPIKE = [
    *("add", "spike", "a spike title"),
    *("--hypothesis", "Can one file per item hold the record?"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "Q-0001", "--output", "an output"]
STARTED = [ADD_SPIKE, ADD_TASK, ["start", "Q-0001"], ["start", "T-0001"]]
TASK_DONE = ["complete", "T-0001", "--commit", "abc1234"]
SPIKE_DONE = [
    *("complete", "Q-0001", "--commit", "def5678"),
    *("--decision", "yes: one file per work item, its Tasks inside"),
]


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


class TestAStartedSpikeWhoseTaskIsCompletedCompletedWithACommitAndItsDecision:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STARTED, TASK_DONE, SPIKE_DONE)

    def test_complete_exits_with_zero(self, completed: Outcome) -> None:
        assert completed.status == 0

    def test_complete_names_the_spike_and_its_commit(self, completed: Outcome) -> None:
        assert completed.out == "completed Q-0001 at def5678\n"

    def test_show_prints_the_decision_under_its_hypothesis(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "Q-0001"], tmp_path).out.splitlines()[:5] == [
            "Q-0001  a spike title",
            "  bucket       Completed",
            "  commit       def5678",
            "  hypothesis   Can one file per item hold the record?",
            "  decision     yes: one file per work item, its Tasks inside",
        ]

    def test_status_lists_it_under_completed_with_its_commit(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (0)\nInProgress (0)\nCompleted (1)\n  Q-0001  def5678  a spike title\n"
        )


def test_a_spike_in_backlog_is_shown_with_its_hypothesis_alone(tmp_path: Path) -> None:
    runs(tmp_path, ADD_STORY, ADD_SPIKE)
    assert fgraph(["show", "Q-0001"], tmp_path).out == (
        "Q-0001  a spike title\n"
        "  bucket       Backlog\n"
        "  hypothesis   Can one file per item hold the record?\n"
        "Tasks (0)\n"
    )


def test_the_hypothesis_of_a_spike_is_amended(tmp_path: Path) -> None:
    runs(tmp_path, ADD_SPIKE, ["amend", "Q-0001", "--hypothesis", "Can one file hold it?"])
    assert fgraph(["show", "Q-0001"], tmp_path).out.splitlines()[2] == (
        "  hypothesis   Can one file hold it?"
    )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([["add", "spike", "a spike title", "--hypothesis", " "]], "hypothesis is empty"),
        (
            [*STARTED, TASK_DONE, ["complete", "Q-0001", "--commit", "def5678"]],
            "Q-0001 is completed with its decision: it states a hypothesis",
        ),
        (
            [*STARTED, TASK_DONE, [*SPIKE_DONE[:4], "--decision", " "]],
            "decision is empty",
        ),
        (
            [*STARTED, [*TASK_DONE, "--decision", "yes"]],
            "T-0001 takes no decision: only a Spike is completed with one",
        ),
        (
            [ADD_STORY, ["amend", "S-0001", "--hypothesis", "Can it?"]],
            "S-0001 has no hypothesis: it states a Given / When / Then",
        ),
        (
            [ADD_SPIKE, ["amend", "Q-0001", "--given", "a state"]],
            "Q-0001 has no given, when or then: it states a hypothesis",
        ),
    ],
    ids=[
        "blank-hypothesis",
        "no-decision",
        "blank-decision",
        "decision-on-a-task",
        "hypothesis-on-a-story",
        "given-on-a-spike",
    ],
)
def test_a_spike_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])


def test_a_story_completed_with_a_decision_is_refused(tmp_path: Path) -> None:
    task = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
    done = ["complete", "S-0001", "--commit", "def5678", "--decision", "yes"]
    outcome = runs(
        tmp_path, ADD_STORY, task, ["start", "S-0001"], ["start", "T-0001"], TASK_DONE, done
    )
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: S-0001 takes no decision: only a Spike is completed with one"],
    )
