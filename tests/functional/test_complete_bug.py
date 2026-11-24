"""The criterion of completing a Bug: `fgraph status` lists it under Completed with its commit.

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
ADD_BUG = [
    *("add", "bug", "a bug title"),
    *("--observed", "it prints a traceback", "--expected", "it exits 2 and names the path"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "B-0001", "--output", "an output"]
STARTED = [ADD_BUG, ADD_TASK, ["start", "B-0001"], ["start", "T-0001"]]
TASK_DONE = ["complete", "T-0001", "--commit", "abc1234"]
BUG_DONE = ["complete", "B-0001", "--commit", "def5678"]


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


class TestAStartedBugWhoseTaskIsCompletedCompletedWithACommit:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STARTED, TASK_DONE, BUG_DONE)

    def test_complete_exits_with_zero(self, completed: Outcome) -> None:
        assert completed.status == 0

    def test_complete_names_the_bug_and_its_commit(self, completed: Outcome) -> None:
        assert completed.out == "completed B-0001 at def5678\n"

    def test_status_lists_it_under_completed_with_that_commit(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "backlog (0)\nin-progress (0)\ncompleted (1)\n  B-0001  def5678  a bug title\n"
        )


def test_a_bug_added_is_named_by_its_own_id(tmp_path: Path) -> None:
    outcome = runs(tmp_path, ADD_STORY, ADD_BUG)
    assert (outcome.status, outcome.out) == (0, "added B-0001\n")


def test_a_bug_is_shown_with_what_is_observed_and_expected(tmp_path: Path) -> None:
    runs(tmp_path, ADD_BUG, ADD_TASK)
    assert fgraph(["show", "B-0001"], tmp_path).out == (
        "B-0001  a bug title\n"
        "  bucket       backlog\n"
        "  observed     it prints a traceback\n"
        "  expected     it exits 2 and names the path\n"
        "Tasks (1)\n"
        "  T-0001  a task title\n"
        "    expected output  an output\n"
    )


def test_a_bug_joins_the_backlog_after_the_work_items_added_before_it(tmp_path: Path) -> None:
    runs(tmp_path, ADD_STORY, ADD_BUG)
    assert fgraph(["status", "--backlog"], tmp_path).out.splitlines()[:3] == [
        "backlog (2)",
        "= S-0001  []  a title",
        "  B-0001  []  a bug title",
    ]


def test_what_is_expected_of_a_bug_is_amended(tmp_path: Path) -> None:
    runs(tmp_path, ADD_BUG, ["amend", "B-0001", "--expected", "it exits 2"])
    assert fgraph(["show", "B-0001"], tmp_path).out.splitlines()[2:4] == [
        "  observed     it prints a traceback",
        "  expected     it exits 2",
    ]


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        (
            [["add", "bug", "a bug title", "--observed", " ", "--expected", "it exits 2"]],
            "observed is empty",
        ),
        (
            [["add", "bug", "a bug title", "--observed", "a traceback", "--expected", ""]],
            "expected is empty",
        ),
        (
            [ADD_BUG, ["amend", "B-0001", "--given", "a state"]],
            "B-0001 has no given, when or then: it states what is observed and expected",
        ),
        (
            [ADD_STORY, ["amend", "S-0001", "--observed", "a traceback"]],
            "S-0001 has no observed or expected: it states a Given / When / Then",
        ),
    ],
    ids=["blank-observed", "blank-expected", "given-on-a-bug", "observed-on-a-story"],
)
def test_a_bug_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])
