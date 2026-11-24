"""The criterion of S-0147: `fgraph remove` takes a Task of a started work item, with its reason.

A Task in Backlog and a started one, each removed with its reason, are kept as removed with it:
they count in no progress of their work item and are no Task left to complete before it lands.
Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it.
"""

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
LATER = START + timedelta(minutes=1)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]


def task(number: int) -> list[str]:
    """The command that adds the Task of that number to S-0001."""
    return ["add", "task", f"task {number}", "--parent", "S-0001", "--output", "an output"]


RECORD = (ADD_STORY, task(1), task(2), task(3), ["start", "S-0001"], ["start", "T-0001"])
DROP_WAITING = ["remove", "T-0002", "--reason", "not needed"]
DROP_STARTED = ["remove", "T-0001", "--reason", "folded into T-0003"]
DROP_LAST = ["remove", "T-0003", "--reason", "not needed either"]
REMOVED = (*RECORD, DROP_WAITING, DROP_STARTED)
LAST_DONE = (["start", "T-0003"], ["complete", "T-0003"])
STORY_DONE = ["complete", "S-0001"]
BLOCK_STORY = ["block", "S-0001", "--reason", "no key", "--waiting-on", "developer"]


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


def held(tasks: Iterable[dict[str, Any]]) -> list[tuple[str, str, str | None]]:
    """The id, the state and the reason of each Task of a JSON document."""
    return [(each["id"], each["state"], each["reason"]) for each in tasks]


SHOWN = (
    "S-0001  a title\n"
    "  bucket       in-progress\n"
    "  given        a state\n"
    "  when         an action\n"
    "  then         another\n"
    "Tasks (3)\n"
    "  T-0001  task 1\n"
    "    bucket           removed\n"
    "    reason           folded into T-0003\n"
    "    expected output  an output\n"
    "  T-0002  task 2\n"
    "    bucket           removed\n"
    "    reason           not needed\n"
    "    expected output  an output\n"
    "  T-0003  task 3\n"
    "    expected output  an output\n"
)
HELD = [
    ("T-0001", "removed", "folded into T-0003"),
    ("T-0002", "removed", "not needed"),
    ("T-0003", "backlog", None),
]


def test_the_remove_of_a_task_in_backlog_names_it_and_its_story(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *RECORD, DROP_WAITING)
    assert (outcome.status, outcome.out) == (0, "removed T-0002 of S-0001\n")


def test_the_remove_of_the_started_task_names_it_and_its_story(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *RECORD, DROP_WAITING, DROP_STARTED)
    assert (outcome.status, outcome.out) == (0, "removed T-0001 of S-0001\n")


class TestATaskInBacklogAndTheStartedOneRemoved:
    @pytest.fixture
    def removed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *REMOVED)

    def test_status_lists_the_story_at_none_of_one_task_and_no_task_under_it(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "backlog (0)\nin-progress (1)\n  S-0001  0/1 T  a title\ncompleted (0)\n"
        )

    def test_show_lists_each_removed_task_with_its_bucket_and_its_reason(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], tmp_path, LATER).out == SHOWN

    def test_brief_lists_the_text_show_lists(self, removed: Outcome, tmp_path: Path) -> None:
        brief = fgraph(["brief", "S-0001"], tmp_path, LATER).out
        shown = fgraph(["show", "S-0001"], tmp_path, LATER).out
        assert (removed.status, brief == shown) == (0, True)

    def test_status_as_json_lists_the_progress_and_each_task_with_its_state_and_reason(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        story = item(tmp_path, "S-0001")
        assert (story["progress"], held(story["tasks"])) == (
            {"completed": 0, "total": 1},
            HELD,
        )

    def test_brief_as_json_lists_each_task_with_its_state_and_reason(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        document = json.loads(fgraph(["brief", "S-0001", "--format", "json"], tmp_path, LATER).out)
        assert held(document["tasks"]) == HELD


class TestTheTaskLeftCompleted:
    @pytest.fixture
    def done(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *REMOVED, *LAST_DONE)

    def test_status_lists_the_story_marked_for_review_at_one_of_one_task(
        self, done: Outcome, tmp_path: Path
    ) -> None:
        lines = fgraph(["status"], tmp_path, LATER).out.splitlines()
        assert "@ S-0001  1/1 T  a title" in lines

    def test_the_story_completes(self, done: Outcome, tmp_path: Path) -> None:
        outcome = runs(tmp_path, STORY_DONE)
        assert (outcome.status, outcome.out) == (0, "completed S-0001\n")

    def test_show_lists_the_tasks_of_the_completed_story_removed_removed_and_completed(
        self, done: Outcome, tmp_path: Path
    ) -> None:
        runs(tmp_path, STORY_DONE)
        lines = fgraph(["show", "S-0001"], tmp_path, LATER).out.splitlines()
        assert [line for line in lines if line.startswith("    bucket")] == [
            "    bucket           removed",
            "    bucket           removed",
            "    bucket           completed",
        ]


class TestEveryTaskRemoved:
    @pytest.fixture
    def emptied(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *REMOVED, DROP_LAST)

    def test_status_lists_the_story_at_none_of_none_unmarked(
        self, emptied: Outcome, tmp_path: Path
    ) -> None:
        lines = fgraph(["status"], tmp_path, LATER).out.splitlines()
        assert "  S-0001  0/0 T  a title" in lines

    def test_the_story_completes(self, emptied: Outcome, tmp_path: Path) -> None:
        outcome = runs(tmp_path, STORY_DONE)
        assert (outcome.status, outcome.out) == (0, "completed S-0001\n")


def test_a_blocked_task_is_removed_as_a_started_one(tmp_path: Path) -> None:
    block = ["block", "T-0001", "--reason", "no key", "--waiting-on", "developer"]
    outcome = runs(tmp_path, *RECORD, block, ["remove", "T-0001", "--reason", "a reason"])
    assert (outcome.status, outcome.out) == (0, "removed T-0001 of S-0001\n")


def refused(argvs: Sequence[Sequence[str]], error: str, id_: str) -> Any:
    """A parameter of the refusals: the commands run and the error the last prints."""
    return pytest.param(argvs, error, id=id_)


def dropped(task_id: str) -> list[str]:
    """The remove of the Task of that id, with a reason."""
    return ["remove", task_id, "--reason", "a reason"]


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        refused(
            [*RECORD, ["complete", "T-0001"], dropped("T-0001")],
            "T-0001 is completed already",
            "completed-task",
        ),
        refused([*RECORD, DROP_WAITING, DROP_WAITING], "T-0002 is removed already", "removed"),
        refused([*RECORD, ["remove", "T-0002", "--reason", " "]], "reason is empty", "blank"),
        refused([*RECORD, dropped("T-0009")], "no Task T-0009 in the record", "no-such-task"),
        refused([*RECORD, dropped("T-0000")], "a Task id counts from 1: 0 is below 1", "task-zero"),
        refused(
            [*RECORD, dropped("X-0001")],
            "'X-0001' is no Story, Upkeep, Bug, Spike, Task or Feature id",
            "no-id",
        ),
        refused(
            [*RECORD, ["remove", "T-0001", "--superseded-by", "S-0001"]],
            "T-0001 is a Task: it is removed with --reason alone",
            "superseded-by",
        ),
        refused(
            [ADD_STORY, task(1), dropped("T-0001")],
            "T-0001 cannot be removed: S-0001 is in Backlog",
            "story-in-backlog",
        ),
        refused(
            [*RECORD, BLOCK_STORY, dropped("T-0002")],
            "T-0002 cannot be removed: S-0001 is blocked, waiting on developer: unblock it first",
            "story-blocked",
        ),
        refused(
            [*REMOVED, ["start", "T-0002"]], "T-0002 is removed already", "start-a-removed-task"
        ),
        refused(
            [*REMOVED, ["complete", "T-0002"]],
            "T-0002 is removed already",
            "complete-a-removed-task",
        ),
        refused(
            [*REMOVED, ["block", "T-0002", "--reason", "r", "--waiting-on", "w"]],
            "T-0002 is removed already",
            "block-a-removed-task",
        ),
    ],
)
def test_a_refusal_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        (
            [*RECORD, STORY_DONE],
            "S-0001 has Tasks to complete first: T-0001, T-0002, T-0003",
        ),
        ([*RECORD, ["remove", "S-0009", "--reason", "r"]], "no Story S-0009 in the record"),
    ],
    ids=["complete-the-story-of-open-tasks", "remove-no-such-story"],
)
def test_a_guard_refused_today_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])
