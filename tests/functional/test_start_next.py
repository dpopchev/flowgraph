"""The criterion of the next work item of a Feature: the completion of the one before starts it.

`fgraph status` lists the second Story started under the Feature once the first is completed; a
second Story without a Task is not started, and the completion stands. Run end to end on a
record in a temporary directory, through the file adapters of the package, each command one
second after the one before it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
LATER = START + timedelta(minutes=1)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
ADD_THIRD = ["add", "story", "a third title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
TASK_FOR_THIRD = ["add", "task", "a task title", "--parent", "S-0003", "--output", "an output"]
SECOND_WITHOUT_A_TASK = (ADD_FEATURE, ADD_STORY, ADD_OTHER, ADD_TASK)
TWO_STORIES = (*SECOND_WITHOUT_A_TASK, TASK_FOR_OTHER)
FIRST_READY = (
    ["start", "F-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
)
COMPLETE_FIRST = ["complete", "S-0001", "--commit", "def5678"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, at: datetime) -> Outcome:
    """Run the command at that time in cwd, whose record is `.fgraph/`, on the files of it."""
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
        now=lambda: at,
    )
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the last; the outcome of the last."""
    outcomes = [
        fgraph(argv, cwd, START + timedelta(seconds=seconds)) for seconds, argv in enumerate(argvs)
    ]
    return outcomes[-1]


class TestTheFirstStoryOfAStartedFeatureCompletedWhileTheSecondIsInBacklog:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *TWO_STORIES, *FIRST_READY, COMPLETE_FIRST)

    def test_complete_names_the_second_story_started_on_a_line_after_the_completion(
        self, completed: Outcome
    ) -> None:
        assert (completed.status, completed.out) == (
            0,
            "completed S-0001 at def5678\nstarted S-0002\n",
        )

    def test_status_lists_the_second_story_started_under_the_feature(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  F-0001  1/2 W  a feature title\n"
            "    S-0002  0/1 T  another title\n"
            "    S-0001  1/1 T  a title\n"
            "Completed (0)\n"
        )

    def test_the_second_story_takes_the_start_of_its_task(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["start", "T-0002"], tmp_path, LATER).out == "started T-0002 of S-0002\n"


def test_the_story_a_completion_starts_is_the_first_in_backlog_in_the_order_of_the_queue(
    tmp_path: Path,
) -> None:
    reorder = ["reorder", "S-0003", "--before", "S-0002"]
    added = (*TWO_STORIES, ADD_THIRD, TASK_FOR_THIRD, reorder)
    assert runs(tmp_path, *added, *FIRST_READY, COMPLETE_FIRST).out == (
        "completed S-0001 at def5678\nstarted S-0003\n"
    )


class TestTheFirstStoryOfAStartedFeatureCompletedWhileTheSecondHasNoTask:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *SECOND_WITHOUT_A_TASK, *FIRST_READY, COMPLETE_FIRST)

    def test_complete_names_the_second_story_not_started_and_why(self, completed: Outcome) -> None:
        assert (completed.status, completed.out) == (
            0,
            "completed S-0001 at def5678\nnot started: S-0002 has no Task to start with\n",
        )

    def test_status_lists_the_feature_in_progress_with_no_story_started_under_it(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  F-0001  1/2 W  a feature title\n"
            "    S-0001  1/1 T  a title\n"
            "Completed (0)\n"
        )
