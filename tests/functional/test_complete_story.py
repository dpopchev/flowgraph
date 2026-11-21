"""The criterion of completing a Story: `fgraph status` lists it under Completed with its commit.

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
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
STARTED = [ADD_STORY, ADD_TASK, ["start", "S-0001"], ["start", "T-0001"]]
TASK_DONE = ["complete", "T-0001", "--commit", "abc1234"]
STORY_DONE = ["complete", "S-0001", "--commit", "def5678"]


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


class TestAStartedStoryWhoseTaskIsCompletedCompleted:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> tuple[Outcome, Outcome]:
        """The outcome of completing the Task of a started Story, then of completing the Story."""
        return runs(tmp_path, *STARTED, TASK_DONE), fgraph(STORY_DONE, tmp_path)

    def test_complete_names_the_task_its_story_and_its_commit(
        self, completed: tuple[Outcome, Outcome]
    ) -> None:
        assert completed[0].out == "completed T-0001 of S-0001 at abc1234\n"

    def test_complete_exits_with_zero(self, completed: tuple[Outcome, Outcome]) -> None:
        assert completed[1].status == 0

    def test_complete_names_the_story_and_its_commit(
        self, completed: tuple[Outcome, Outcome]
    ) -> None:
        assert completed[1].out == "completed S-0001 at def5678\n"

    def test_status_lists_it_under_completed_with_that_commit(
        self, completed: tuple[Outcome, Outcome], tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (0)\nInProgress (0)\nCompleted (1)\n  S-0001  def5678  a title\n"
        )

    def test_show_names_the_bucket_and_commit_of_each(
        self, completed: tuple[Outcome, Outcome], tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], tmp_path).out == (
            "S-0001  a title\n"
            "  bucket       Completed\n"
            "  commit       def5678\n"
            "  given        a state\n"
            "  when         an action\n"
            "  then         another\n"
            "Tasks (1)\n"
            "  T-0001  a task title\n"
            "    bucket           Completed\n"
            "    commit           abc1234\n"
            "    expected output  an output\n"
        )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([*STARTED, STORY_DONE], "S-0001 has Tasks to complete first: T-0001"),
        ([ADD_STORY, ADD_TASK, STORY_DONE], "S-0001 is in Backlog: start it first"),
        (
            [ADD_STORY, ADD_TASK, ["start", "S-0001"], TASK_DONE],
            "T-0001 is in Backlog: start it first",
        ),
        ([ADD_STORY, ADD_TASK, TASK_DONE], "T-0001 is in Backlog: start it first"),
        ([*STARTED, TASK_DONE, TASK_DONE], "T-0001 is completed already"),
        ([*STARTED, TASK_DONE, STORY_DONE, STORY_DONE], "S-0001 is completed already"),
        ([*STARTED, TASK_DONE, STORY_DONE, ["start", "S-0001"]], "S-0001 is completed already"),
        ([*STARTED, TASK_DONE, STORY_DONE, ADD_TASK], "S-0001 is completed already"),
        (
            [*STARTED, ["complete", "T-0001", "--commit", "xyz"]],
            "'xyz' is no commit: it is 7 to 40 hex digits",
        ),
        ([["complete", "S-0002", "--commit", "abc1234"]], "no Story S-0002 in the record"),
        ([*STARTED, ["complete", "T-0002", "--commit", "abc1234"]], "no Task T-0002 in the record"),
    ],
    ids=[
        "story-with-a-task-open",
        "story-in-backlog",
        "task-in-backlog",
        "task-of-story-in-backlog",
        "task-completed-twice",
        "story-completed-twice",
        "completed-story-started",
        "task-added-to-completed-story",
        "no-commit",
        "unknown-story",
        "unknown-task",
    ],
)
def test_a_complete_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")
