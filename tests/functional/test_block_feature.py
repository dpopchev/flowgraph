"""The criterion of blocking a Feature: `fgraph status` lists it under InProgress with `!`.

The line of a started Feature blocked with a reason and what it waits on starts with `!` and
ends with what it waits on. Run end to end on a record in a temporary directory, through the
file adapters of the package, each command one second after the one before it.
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
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
BLOCK = ["block", "F-0001", "--reason", "the budget is not agreed", "--waiting-on", "the sponsor"]
BLOCK_TASK = ["block", "T-0001", "--reason", "no review", "--waiting-on", "the reviewer"]
ADDED = (ADD_FEATURE, ADD_STORY, ADD_TASK)
STARTED = (*ADDED, ["start", "F-0001"])
TWO_STORIES = (*ADDED, ADD_OTHER, TASK_FOR_OTHER, ["start", "F-0001"])
TASK_DONE = (["start", "T-0001"], ["complete", "T-0001", "--commit", "abc1234"])
COMPLETE_STORY = ["complete", "S-0001", "--commit", "def5678"]
HELD = "F-0001 is blocked, waiting on the sponsor: unblock it first"
MARKED = "! F-0001  0/1 W  a feature title  -- waiting on the sponsor: the budget is not agreed"


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


class TestAStartedFeatureBlockedWithAReasonAndWhatItWaitsOn:
    @pytest.fixture
    def blocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STARTED, BLOCK)

    def test_block_exits_with_zero(self, blocked: Outcome) -> None:
        assert blocked.status == 0

    def test_block_names_the_feature(self, blocked: Outcome) -> None:
        assert blocked.out == "blocked F-0001\n"

    def test_status_lists_it_under_inprogress_with_the_mark_and_what_it_waits_on(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            f"Backlog (0)\nInProgress (1)\n{MARKED}\n    S-0001  0/1 T  a title\nCompleted (0)\n"
        )

    def test_show_lists_it_in_inprogress_as_blocked_with_its_reason_and_what_it_waits_on(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "F-0001"], tmp_path, LATER).out == (
            "F-0001  a feature title\n"
            "  bucket       InProgress, blocked\n"
            "  reason       the budget is not agreed\n"
            "  waiting on   the sponsor\n"
            "Criteria (1)\n"
            "  a criterion\n"
            "Work items (1)\n"
            "  S-0001  a title  InProgress\n"
        )

    def test_its_started_story_goes_on_with_the_start_of_its_task(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["start", "T-0001"], tmp_path, LATER).out == "started T-0001 of S-0001\n"

    def test_its_own_block_is_listed_before_that_of_a_task_of_its_story(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        runs(tmp_path, ["start", "T-0001"], BLOCK_TASK)
        assert fgraph(["status"], tmp_path, LATER).out.splitlines()[2:5] == [
            MARKED,
            "    S-0001  0/1 T  a title",
            "      !  T-0001  a task title  -- waiting on the reviewer: no review",
        ]

    def test_the_completion_of_its_last_story_completes_it(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert runs(tmp_path, *TASK_DONE, COMPLETE_STORY).out == (
            "completed S-0001 at def5678\ncompleted F-0001 at def5678\n"
        )


class TestAStartedFeatureBlockedWhileItHoldsAStoryInBacklog:
    @pytest.fixture
    def blocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *TWO_STORIES, BLOCK)

    def test_the_start_of_the_story_in_backlog_is_refused_naming_the_block(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        outcome = fgraph(["start", "S-0002"], tmp_path, LATER)
        assert (outcome.status, outcome.err.splitlines()[-1:]) == (
            2,
            [f"fgraph: error: S-0002 cannot start: {HELD}"],
        )

    def test_the_completion_of_its_started_story_stands_and_names_the_next_not_started(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        completed = runs(tmp_path, *TASK_DONE, COMPLETE_STORY)
        assert (completed.status, completed.out) == (
            0,
            f"completed S-0001 at def5678\nnot started: S-0002 cannot start: {HELD}\n",
        )

    def test_status_lists_it_blocked_with_no_story_started_under_it_after_that_completion(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        runs(tmp_path, *TASK_DONE, COMPLETE_STORY)
        assert fgraph(["status"], tmp_path, LATER).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "! F-0001  1/2 W  a feature title  "
            "-- waiting on the sponsor: the budget is not agreed\n"
            "Completed (0)\n"
        )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([*ADDED, BLOCK], "F-0001 is in Backlog: start it first"),
        ([*STARTED, BLOCK, BLOCK], "F-0001 is blocked already"),
        ([*STARTED, *TASK_DONE, COMPLETE_STORY, BLOCK], "F-0001 is completed already"),
        (
            [*STARTED, ["block", "F-0001", "--reason", " ", "--waiting-on", "the sponsor"]],
            "reason is empty",
        ),
        (
            [*STARTED, ["block", "F-0001", "--reason", "a reason", "--waiting-on", ""]],
            "waiting on is empty",
        ),
        (
            [*STARTED, ["block", "F-0009", "--reason", "a reason", "--waiting-on", "someone"]],
            "no Feature F-0009 in the record",
        ),
        ([*STARTED, BLOCK, ["start", "F-0001"]], "F-0001 is blocked: unblock it first"),
        (
            [["block", "S-0001", "--reason", "a reason", "--waiting-on", "someone"]],
            "no Story S-0001 in the record",
        ),
        (
            [["unblock", "X-0001"]],
            "'X-0001' is no Story, Upkeep, Bug, Spike, Task or Feature id",
        ),
        ([["unblock", "F-0000"]], "a Feature id counts from 1: 0 is below 1"),
    ],
    ids=[
        "feature-in-backlog",
        "blocked-already",
        "completed-already",
        "blank-reason",
        "blank-waiting-on",
        "no-such-feature",
        "start-a-blocked-feature",
        "block-of-a-story-id",
        "unblock-of-no-id",
        "unblock-of-a-feature-id-below-one",
    ],
)
def test_a_block_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])
