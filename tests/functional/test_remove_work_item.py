"""The criterion of removing a work item: `fgraph status` lists it under Removed with its reason.

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
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
REMOVE = ["remove", "S-0001", "--reason", "filed by mistake"]
START = ["start", "S-0001"]


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


class TestAStoryInBacklogRemovedWithAReason:
    @pytest.fixture
    def removed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_TASK, ADD_OTHER, REMOVE)

    def test_remove_exits_with_zero(self, removed: Outcome) -> None:
        assert removed.status == 0

    def test_remove_names_the_story(self, removed: Outcome) -> None:
        assert removed.out == "removed S-0001\n"

    def test_status_lists_it_under_removed_with_its_reason(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (1)\n"
            "> S-0002  []  another title\n"
            "InProgress (0)\n"
            "Completed (0)\n"
            "Removed (1)\n"
            "  S-0001  a title  -- filed by mistake\n"
        )

    def test_show_names_the_bucket_and_the_reason_and_keeps_its_task(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], tmp_path).out == (
            "S-0001  a title\n"
            "  bucket       Removed\n"
            "  reason       filed by mistake\n"
            "  given        a state\n"
            "  when         an action\n"
            "  then         another\n"
            "Tasks (1)\n"
            "  T-0001  a task title\n"
            "    expected output  an output\n"
        )


class TestAStartedStoryWithATaskCompletedAndOneInBacklogRemoved:
    @pytest.fixture
    def removed(self, tmp_path: Path) -> Outcome:
        worked = (START, ["start", "T-0001"], ["complete", "T-0001", "--commit", "abc1234"])
        return runs(tmp_path, ADD_STORY, ADD_TASK, ADD_TASK, *worked, REMOVE)

    def test_remove_names_the_story(self, removed: Outcome) -> None:
        assert (removed.status, removed.out) == (0, "removed S-0001\n")

    def test_status_lists_it_under_removed(self, removed: Outcome, tmp_path: Path) -> None:
        assert "Removed (1)\n  S-0001  a title  -- filed by mistake\n" in (
            fgraph(["status"], tmp_path).out
        )

    def test_show_keeps_its_completed_task_and_removes_the_other(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        lines = fgraph(["show", "S-0001"], tmp_path).out.splitlines()
        assert [line.split()[-1] for line in lines if line.startswith("    bucket")] == [
            "Completed",
            "Removed",
        ]


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_STORY, REMOVE, REMOVE], "S-0001 is removed already"),
        ([ADD_STORY, ["remove", "S-0001", "--reason", " "]], "reason is empty"),
        (
            [ADD_STORY, ["remove", "S-0009", "--reason", "a reason"]],
            "no Story S-0009 in the record",
        ),
        (
            [ADD_STORY, ADD_TASK, ["remove", "T-0001", "--reason", "a reason"]],
            "T-0001 cannot be removed: S-0001 is in Backlog",
        ),
        ([ADD_STORY, REMOVE, ADD_TASK], "S-0001 is removed already"),
        ([ADD_STORY, ADD_TASK, REMOVE, START], "S-0001 is removed already"),
        (
            [ADD_STORY, REMOVE, ["amend", "S-0001", "--title", "one more"]],
            "S-0001 is removed already",
        ),
        (
            [ADD_STORY, ADD_OTHER, REMOVE, ["reorder", "S-0002", "--before", "S-0001"]],
            "S-0001 is not in Backlog",
        ),
    ],
    ids=[
        "removed-already",
        "blank-reason",
        "no-such-story",
        "a-task-id",
        "task-for-a-removed-story",
        "start-a-removed-story",
        "amend-a-removed-story",
        "reorder-before-a-removed-story",
    ],
)
def test_a_remove_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])


def test_status_of_a_record_with_nothing_removed_lists_no_removed_heading(tmp_path: Path) -> None:
    assert fgraph(["status"], tmp_path).out == "Backlog (0)\nInProgress (0)\nCompleted (0)\n"
