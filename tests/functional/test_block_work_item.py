"""The criterion of S-0138: `fgraph status` lists a blocked work item with its reason.

A started work item blocked with a reason and what it waits on is listed under InProgress with
`!` and what it waits on, and after its unblock as started again. Run end to end on a record in
a temporary directory, through the file adapters of the package, each command one second after
the one before it.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

RED = pytest.mark.xfail(strict=True, reason="S-0138: the block of a work item is not built")
START = datetime(2026, 1, 1, tzinfo=UTC)
LATER = START + timedelta(minutes=1)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
START_STORY = ["start", "S-0001"]
BLOCK = ["block", "S-0001", "--reason", "no key", "--waiting-on", "developer"]
UNBLOCK = ["unblock", "S-0001"]
STARTED = (ADD_STORY, ADD_TASK, START_STORY)
START_TASK = ["start", "T-0001"]
TASK_DONE = (START_TASK, ["complete", "T-0001", "--commit", "abc1234"])
MARKED = "! S-0001  0/1 T  a title  -- waiting on developer: no key"


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


def item(cwd: Path, id_: str) -> dict[str, Any]:
    """The item of that id in the JSON of `fgraph status`, found in any bucket of it."""
    document = json.loads(fgraph(["status", "--format", "json"], cwd, LATER).out)
    return next(each for b in document["buckets"] for each in b["items"] if each["id"] == id_)


class TestAStartedStoryBlocked:
    @pytest.fixture
    def blocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STARTED, BLOCK)

    @RED
    def test_block_exits_with_zero(self, blocked: Outcome) -> None:
        assert blocked.status == 0

    @RED
    def test_block_names_the_story(self, blocked: Outcome) -> None:
        assert blocked.out == "blocked S-0001\n"

    @RED
    def test_status_lists_it_under_inprogress_with_the_mark_and_what_it_waits_on(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            f"Backlog (0)\nInProgress (1)\n{MARKED}\nCompleted (0)\n"
        )

    @RED
    def test_show_lists_it_in_inprogress_as_blocked_with_its_reason_and_what_it_waits_on(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], tmp_path, LATER).out == (
            "S-0001  a title\n"
            "  bucket       InProgress, blocked\n"
            "  reason       no key\n"
            "  waiting on   developer\n"
            "  given        a state\n"
            "  when         an action\n"
            "  then         another\n"
            "Tasks (1)\n"
            "  T-0001  a task title\n"
            "    expected output  an output\n"
        )

    @RED
    def test_the_json_holds_its_state_blocked_and_its_block(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        listed = item(tmp_path, "S-0001")
        assert (listed["state"], listed["block"]) == (
            "blocked",
            {"reason": "no key", "waiting_on": "developer"},
        )

    @RED
    def test_its_started_task_is_listed_right_under_it(self, tmp_path: Path) -> None:
        runs(tmp_path, *STARTED, START_TASK, BLOCK)
        assert fgraph(["status"], tmp_path, LATER).out.splitlines()[2:4] == [
            MARKED,
            "    => T-0001  a task title",
        ]


class TestABlockedStoryUnblocked:
    @pytest.fixture
    def unblocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STARTED, BLOCK, UNBLOCK)

    @RED
    def test_unblock_exits_with_zero(self, unblocked: Outcome) -> None:
        assert unblocked.status == 0

    @RED
    def test_unblock_names_the_story(self, unblocked: Outcome) -> None:
        assert unblocked.out == "unblocked S-0001\n"

    @RED
    def test_status_lists_it_as_started_again(self, unblocked: Outcome, tmp_path: Path) -> None:
        assert (unblocked.status, fgraph(["status"], tmp_path, LATER).out) == (
            0,
            "Backlog (0)\nInProgress (1)\n  S-0001  0/1 T  a title\nCompleted (0)\n",
        )

    @RED
    def test_the_json_holds_its_state_started_and_no_block(
        self, unblocked: Outcome, tmp_path: Path
    ) -> None:
        listed = item(tmp_path, "S-0001")
        assert (listed["state"], listed["block"]) == ("started", None)

    @RED
    def test_it_is_blocked_a_second_time(self, unblocked: Outcome, tmp_path: Path) -> None:
        assert fgraph(BLOCK, tmp_path, LATER).out == "blocked S-0001\n"


@pytest.mark.parametrize(
    ("added", "id_"),
    [
        pytest.param(
            ["add", "upkeep", "an upkeep title", *CRITERION], "U-0001", marks=RED, id="upkeep"
        ),
        pytest.param(
            ["add", "bug", "a bug title", "--observed", "a traceback", "--expected", "exit 2"],
            "B-0001",
            marks=RED,
            id="bug",
        ),
        pytest.param(
            ["add", "spike", "a spike title", "--hypothesis", "Can it be blocked?"],
            "Q-0001",
            marks=RED,
            id="spike",
        ),
    ],
)
def test_a_work_item_of_another_kind_is_blocked(added: list[str], id_: str, tmp_path: Path) -> None:
    task = ["add", "task", "a task title", "--parent", id_, "--output", "an output"]
    blocked = runs(
        tmp_path,
        added,
        task,
        ["start", id_],
        ["block", id_, "--reason", "no key", "--waiting-on", "developer"],
    )
    assert blocked.out == f"blocked {id_}\n"


@RED
def test_a_feature_is_marked_by_its_blocked_story(tmp_path: Path) -> None:
    runs(
        tmp_path,
        ["add", "feature", "a feature title", "--criterion", "a criterion"],
        [*ADD_STORY, "--parent", "F-0001"],
        ADD_TASK,
        ["start", "F-0001"],
        BLOCK,
    )
    assert fgraph(["status"], tmp_path, LATER).out.splitlines()[2:4] == [
        "! F-0001  0/1 W  a feature title  -- waiting on developer: no key",
        f"  {MARKED}",
    ]


def test_the_block_of_a_started_task_still_names_its_work_item(tmp_path: Path) -> None:
    blocked = runs(
        tmp_path,
        *STARTED,
        START_TASK,
        ["block", "T-0001", "--reason", "no review", "--waiting-on", "the reviewer"],
    )
    assert blocked.out == "blocked T-0001 of S-0001\n"


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        pytest.param(
            [ADD_STORY, ADD_TASK, BLOCK],
            "S-0001 is in Backlog: start it first",
            marks=RED,
            id="story-in-backlog",
        ),
        pytest.param(
            [*STARTED, BLOCK, BLOCK], "S-0001 is blocked already", marks=RED, id="blocked-already"
        ),
        pytest.param(
            [*STARTED, *TASK_DONE, ["complete", "S-0001", "--commit", "def5678"], BLOCK],
            "S-0001 is completed already",
            marks=RED,
            id="completed-already",
        ),
        pytest.param(
            [*STARTED, ["block", "S-0001", "--reason", " ", "--waiting-on", "developer"]],
            "reason is empty",
            marks=RED,
            id="blank-reason",
        ),
        pytest.param(
            [*STARTED, ["block", "S-0001", "--reason", "no key", "--waiting-on", ""]],
            "waiting on is empty",
            marks=RED,
            id="blank-waiting-on",
        ),
        pytest.param(
            [*STARTED, ["block", "S-0009", "--reason", "no key", "--waiting-on", "developer"]],
            "no Story S-0009 in the record",
            marks=RED,
            id="no-such-story",
        ),
        pytest.param(
            [*STARTED, UNBLOCK], "S-0001 is not blocked", marks=RED, id="unblock-of-a-started-one"
        ),
        pytest.param(
            [["block", "X-0001", "--reason", "no key", "--waiting-on", "developer"]],
            "'X-0001' is no Story, Upkeep, Bug, Spike, Task or Feature id",
            marks=RED,
            id="block-of-no-id",
        ),
        pytest.param(
            [*STARTED, BLOCK, START_STORY],
            "S-0001 is blocked: unblock it first",
            marks=RED,
            id="start-a-blocked-story",
        ),
        pytest.param(
            [*STARTED, *TASK_DONE, BLOCK, ["complete", "S-0001", "--commit", "def5678"]],
            "S-0001 is blocked: unblock it first",
            marks=RED,
            id="complete-a-blocked-story",
        ),
        pytest.param(
            [*STARTED, BLOCK, START_TASK],
            "T-0001 cannot start: S-0001 is blocked, waiting on developer: unblock it first",
            marks=RED,
            id="start-a-task-of-a-blocked-story",
        ),
        pytest.param(
            [["block", "T-0000", "--reason", "no key", "--waiting-on", "developer"]],
            "a Task id counts from 1: 0 is below 1",
            id="a-task-id-below-one",
        ),
        pytest.param(
            [["block", "F-0000", "--reason", "no key", "--waiting-on", "developer"]],
            "a Feature id counts from 1: 0 is below 1",
            id="a-feature-id-below-one",
        ),
    ],
)
def test_a_block_or_an_unblock_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])
