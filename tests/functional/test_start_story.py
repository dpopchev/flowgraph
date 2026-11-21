"""The criterion of starting a Story: once started, `fgraph status` lists it under InProgress.

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
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]


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


class TestAStoryInBacklogWithOneTaskStarted:
    @pytest.fixture
    def started(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_TASK, ["start", "ST-0001"])

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_start_names_the_story(self, started: Outcome) -> None:
        assert started.out == "started ST-0001\n"

    def test_status_lists_it_under_in_progress(self, started: Outcome, tmp_path: Path) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (0)\nInProgress (1)\n  ST-0001  a title\nCompleted (0)\n"
        )

    def test_show_names_its_bucket(self, started: Outcome, tmp_path: Path) -> None:
        assert "  bucket       InProgress\n" in fgraph(["show", "ST-0001"], tmp_path).out


class TestATaskOfAStartedStoryStarted:
    @pytest.fixture
    def started(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_TASK, ["start", "ST-0001"], ["start", "T-0001"])

    def test_start_names_the_task_and_its_story(self, started: Outcome) -> None:
        assert started.out == "started T-0001 of ST-0001\n"

    def test_show_lists_the_task_in_progress(self, started: Outcome, tmp_path: Path) -> None:
        assert fgraph(["show", "ST-0001"], tmp_path).out.endswith(
            "Tasks (1)\n"
            "  T-0001  a task title\n"
            "    bucket           InProgress\n"
            "    expected output  an output\n"
        )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_STORY, ["start", "ST-0001"]], "ST-0001 has no Task to start with"),
        ([ADD_STORY, ADD_TASK, ["start", "T-0001"]], "T-0001 cannot start: ST-0001 is in Backlog"),
        (
            [ADD_STORY, ADD_TASK, ["start", "ST-0001"], ["start", "ST-0001"]],
            "ST-0001 is started already",
        ),
        (
            [ADD_STORY, ADD_TASK, ["start", "ST-0001"], ["start", "T-0001"], ["start", "T-0001"]],
            "T-0001 is started already",
        ),
        ([["start", "ST-0002"]], "no Story ST-0002 in the record"),
        ([ADD_STORY, ADD_TASK, ["start", "T-0002"]], "no Task T-0002 in the record"),
        ([["start", "B-0001"]], "'B-0001' is no Story, Upkeep or Task id"),
    ],
    ids=[
        "story-without-task",
        "task-of-story-in-backlog",
        "story-started-twice",
        "task-started-twice",
        "unknown-story",
        "unknown-task",
        "no-id",
    ],
)
def test_a_start_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")
