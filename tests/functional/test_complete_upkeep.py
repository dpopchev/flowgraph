"""The criterion of completing an Upkeep: `fgraph status` lists it under Completed with its commit.

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
ADD_UPKEEP = [
    *("add", "upkeep", "an upkeep title"),
    *("--given", "a behavior", "--when", "it runs", "--then", "it still holds"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "U-0001", "--output", "an output"]
STARTED = [ADD_UPKEEP, ADD_TASK, ["start", "U-0001"], ["start", "T-0001"]]
TASK_DONE = ["complete", "T-0001", "--commit", "abc1234"]
UPKEEP_DONE = ["complete", "U-0001", "--commit", "def5678"]


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


class TestAStartedUpkeepWhoseTaskIsCompletedCompleted:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> list[Outcome]:
        """The outcome of each move: write the Task, start both, complete both."""
        fgraph(ADD_UPKEEP, tmp_path)
        argvs = [ADD_TASK, ["start", "U-0001"], ["start", "T-0001"], TASK_DONE, UPKEEP_DONE]
        return [fgraph(argv, tmp_path) for argv in argvs]

    def test_each_move_names_what_it_moved(self, completed: list[Outcome]) -> None:
        assert [outcome.out for outcome in completed] == [
            "added T-0001 to U-0001\n",
            "started U-0001\n",
            "started T-0001 of U-0001\n",
            "completed T-0001 of U-0001 at abc1234\n",
            "completed U-0001 at def5678\n",
        ]

    def test_status_lists_it_under_completed_with_that_commit(
        self, completed: list[Outcome], tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (0)\nInProgress (0)\nCompleted (1)\n  U-0001  def5678  an upkeep title\n"
        )

    def test_show_names_the_bucket_and_commit_of_each(
        self, completed: list[Outcome], tmp_path: Path
    ) -> None:
        assert fgraph(["show", "U-0001"], tmp_path).out == (
            "U-0001  an upkeep title\n"
            "  bucket       Completed\n"
            "  commit       def5678\n"
            "  given        a behavior\n"
            "  when         it runs\n"
            "  then         it still holds\n"
            "Tasks (1)\n"
            "  T-0001  a task title\n"
            "    bucket           Completed\n"
            "    commit           abc1234\n"
            "    expected output  an output\n"
        )


def test_a_task_id_counts_across_stories_and_upkeeps(tmp_path: Path) -> None:
    story_task = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
    assert runs(tmp_path, ADD_STORY, story_task, ADD_UPKEEP, ADD_TASK).out == (
        "added T-0002 to U-0001\n"
    )


def test_an_upkeep_in_progress_is_listed_under_in_progress(tmp_path: Path) -> None:
    assert runs(tmp_path, *STARTED, ["status"]).out == (
        "Backlog (0)\n"
        "InProgress (1)\n"
        "  U-0001  0/1 T  an upkeep title\n"
        "    => T-0001  a task title\n"
        "Completed (0)\n"
    )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_UPKEEP, ["start", "U-0001"]], "U-0001 has no Task to start with"),
        ([*STARTED, UPKEEP_DONE], "U-0001 has Tasks to complete first: T-0001"),
        ([ADD_UPKEEP, ADD_TASK, UPKEEP_DONE], "U-0001 is in Backlog: start it first"),
        ([ADD_UPKEEP, ADD_TASK, ["start", "T-0001"]], "T-0001 cannot start: U-0001 is in Backlog"),
        ([*STARTED, TASK_DONE, UPKEEP_DONE, ADD_TASK], "U-0001 is completed already"),
        ([*STARTED, TASK_DONE, UPKEEP_DONE, ["start", "U-0001"]], "U-0001 is completed already"),
        ([["start", "U-0009"]], "no Upkeep U-0009 in the record"),
        (
            [["add", "task", "t", "--parent", "U-0009", "--output", "o"]],
            "no Upkeep U-0009 in the record",
        ),
        ([["start", "X-0001"]], "'X-0001' is no Story, Upkeep, Bug, Spike or Task id"),
    ],
    ids=[
        "upkeep-without-task",
        "upkeep-with-a-task-open",
        "upkeep-in-backlog",
        "task-of-upkeep-in-backlog",
        "task-added-to-completed-upkeep",
        "completed-upkeep-started",
        "unknown-upkeep",
        "task-for-unknown-upkeep",
        "no-id",
    ],
)
def test_a_move_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")
