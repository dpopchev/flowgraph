"""The amend of a Task in Backlog: each part rewritten alone or with others, the rest as it was."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    StartedAlreadyError,
    TaskAmendment,
    TaskRemovedError,
    TaskState,
    amended,
    blocked,
    completed,
    make_task,
    make_task_id,
    removed,
    started,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_task_id(1)
TASK = make_task(ID, "a task", "an output", "how", CREATED, "make test")
BEGUN = started(TASK, ON)
DONE = completed(BEGUN, ON, make_commit("abc1234"))


@pytest.mark.parametrize(
    ("amendment", "expected"),
    [
        (TaskAmendment(title="another"), replace(TASK, title="another")),
        (TaskAmendment(expected_output="another"), replace(TASK, expected_output="another")),
        (TaskAmendment(check="make lint"), replace(TASK, check="make lint")),
        (TaskAmendment(description="why"), replace(TASK, description="why")),
    ],
    ids=["title", "output", "check", "description"],
)
def test_each_part_given_alone_is_rewritten_and_the_rest_is_kept(
    amendment: TaskAmendment, expected: TaskState
) -> None:
    assert amended(TASK, amendment) == expected


def test_several_parts_given_together_are_rewritten() -> None:
    amendment = TaskAmendment(title="another", expected_output="other output")
    assert amended(TASK, amendment) == replace(
        TASK, title="another", expected_output="other output"
    )


def test_a_blank_description_clears_it() -> None:
    assert amended(TASK, TaskAmendment(description=" ")).description == ""


@pytest.mark.parametrize(
    ("amendment", "part"),
    [
        (TaskAmendment(title=" "), "title"),
        (TaskAmendment(expected_output=""), "output"),
        (TaskAmendment(check=" "), "check"),
    ],
    ids=["title", "output", "check"],
)
def test_a_blank_title_output_or_check_is_refused_naming_it(
    amendment: TaskAmendment, part: str
) -> None:
    with pytest.raises(EmptyPartError, match=f"^{part} is empty$"):
        amended(TASK, amendment)


def test_a_check_given_to_a_task_that_held_none_is_kept() -> None:
    bare = make_task(ID, "a task", "an output", "", CREATED)
    assert amended(bare, TaskAmendment(check="make lint")).check == "make lint"


@pytest.mark.parametrize(
    ("task", "error", "line"),
    [
        (BEGUN, StartedAlreadyError, "T-0001 is started already"),
        (blocked(BEGUN, "no key", "developer", ON), BlockedError, "T-0001 is blocked"),
        (DONE, CompletedAlreadyError, "T-0001 is completed already"),
        (removed(TASK, "not needed", ON), TaskRemovedError, "T-0001 is removed already"),
    ],
    ids=["started", "blocked", "completed", "removed"],
)
def test_a_task_that_is_not_in_backlog_is_refused_with_its_whole_line(
    task: TaskState, error: type[ValueError], line: str
) -> None:
    with pytest.raises(error, match=f"^{line}$"):
        amended(task, TaskAmendment(title="another"))
