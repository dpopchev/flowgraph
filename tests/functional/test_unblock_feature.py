"""Unblocking a Feature: it is started again, and its next work item starts when none is.

A blocked Feature unblocked while its Story is started only loses its mark; one whose started
Story was completed while it was blocked starts the next one, as that completion would have. Run
end to end on a record in a temporary directory, through the file adapters of the package, each
command one second after the one before it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from tests.functional.completed_story import COMPLETIONS as FIRST_DONE

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
LATER = START + timedelta(minutes=1)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
BLOCK = ["block", "F-0001", "--reason", "the budget is not agreed", "--waiting-on", "the sponsor"]
UNBLOCK = ["unblock", "F-0001"]
ADDED = (ADD_FEATURE, ADD_STORY, ADD_TASK)
STARTED = (*ADDED, ["start", "F-0001"])
BLOCKED = (*STARTED, BLOCK)
SECOND_WITHOUT_A_TASK = (*ADDED, ADD_OTHER, ["start", "F-0001"], BLOCK, *FIRST_DONE)
NONE_STARTED = (*ADDED, ADD_OTHER, TASK_FOR_OTHER, ["start", "F-0001"], BLOCK, *FIRST_DONE)


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


class TestABlockedFeatureUnblockedWhileItsStoryIsStarted:
    @pytest.fixture
    def unblocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *BLOCKED, UNBLOCK)

    def test_unblock_exits_with_zero_and_names_the_feature_alone(self, unblocked: Outcome) -> None:
        assert (unblocked.status, unblocked.out) == (0, "unblocked F-0001\n")

    def test_status_lists_it_under_inprogress_without_the_mark(
        self, unblocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "backlog (0)\n"
            "in-progress (1)\n"
            "  F-0001  0/1 W  a feature title\n"
            "    S-0001  0/1 T  a title\n"
            "completed (0)\n"
        )

    def test_show_lists_it_in_inprogress_with_no_block(
        self, unblocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "F-0001"], tmp_path, LATER).out.splitlines()[:3] == [
            "F-0001  a feature title",
            "  bucket       in-progress",
            "Criteria (1)",
        ]

    def test_it_can_be_blocked_once_more(self, unblocked: Outcome, tmp_path: Path) -> None:
        assert fgraph(BLOCK, tmp_path, LATER).out == "blocked F-0001\n"


class TestABlockedFeatureUnblockedWhileNoStoryOfItIsStarted:
    @pytest.fixture
    def unblocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *NONE_STARTED, UNBLOCK)

    def test_unblock_names_the_next_story_started_on_a_line_after_the_unblock(
        self, unblocked: Outcome
    ) -> None:
        assert (unblocked.status, unblocked.out) == (0, "unblocked F-0001\nstarted S-0002\n")

    def test_status_lists_the_next_story_started_under_the_feature_without_the_mark(
        self, unblocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "backlog (0)\n"
            "in-progress (1)\n"
            "  F-0001  1/2 W  a feature title\n"
            "    S-0002  0/1 T  another title\n"
            "    S-0001  1/1 T  a title\n"
            "completed (0)\n"
        )


class TestABlockedFeatureUnblockedWhileItsNextStoryHasNoTask:
    @pytest.fixture
    def unblocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *SECOND_WITHOUT_A_TASK, UNBLOCK)

    def test_unblock_names_the_next_story_not_started_and_why(self, unblocked: Outcome) -> None:
        assert (unblocked.status, unblocked.out) == (
            0,
            "unblocked F-0001\nnot started: S-0002 has no Task to start with\n",
        )

    def test_the_unblock_stands(self, unblocked: Outcome, tmp_path: Path) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "backlog (0)\n"
            "in-progress (1)\n"
            "  F-0001  1/2 W  a feature title\n"
            "    S-0001  1/1 T  a title\n"
            "completed (0)\n"
        )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([*ADDED, UNBLOCK], "F-0001 is not blocked"),
        ([*STARTED, UNBLOCK], "F-0001 is not blocked"),
        ([*STARTED, *FIRST_DONE, UNBLOCK], "F-0001 is not blocked"),
        ([*BLOCKED, UNBLOCK, UNBLOCK], "F-0001 is not blocked"),
        ([*BLOCKED, ["unblock", "F-0009"]], "no Feature F-0009 in the record"),
    ],
    ids=[
        "feature-in-backlog",
        "feature-started",
        "feature-completed",
        "unblocked-already",
        "no-such-feature",
    ],
)
def test_an_unblock_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])
