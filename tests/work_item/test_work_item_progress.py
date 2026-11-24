"""The progress lines of a work item: made, read as rows and kept on it through every move."""

from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit, make_scenario
from flowgraph.task import TaskNotFoundError, make_task, make_task_id
from flowgraph.work_item import (
    Amendment,
    ProgressLine,
    ProgressRow,
    WorkItemState,
    amended_work_item,
    append_task,
    blocked_work_item,
    completed_task,
    completed_work_item,
    make_kind,
    make_progress_line,
    make_work_item,
    make_work_item_id,
    progress_row,
    progressed_work_item,
    removed_work_item,
    started_task,
    started_work_item,
    unblocked_work_item,
)

pytestmark = pytest.mark.model

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
BARE = make_work_item(make_work_item_id(CHORE, 1), "a title", SCENARIO, "", CREATED)
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ITEM = append_task(BARE, TASK)
HALF = started_task(started_work_item(ITEM, ON), make_task_id(3), ON)
STUCK = blocked_work_item(HALF, "no key", "developer", ON)
DONE = completed_task(HALF, make_task_id(3), ON, COMMIT)


@pytest.fixture
def line() -> ProgressLine:
    """A progress line of the work item itself, noted ON."""
    return make_progress_line("a text", ON)


@pytest.fixture
def of_task() -> ProgressLine:
    """A progress line of T-0003, noted ON."""
    return make_progress_line("a text", ON, make_task_id(3))


def test_a_progress_line_holds_its_text(line: ProgressLine) -> None:
    assert line.text == "a text"


def test_a_progress_line_keeps_its_time_to_the_second() -> None:
    noted = make_progress_line("a text", ON.replace(microsecond=500)).noted
    assert noted == ON


def test_a_progress_line_names_no_task_by_default(line: ProgressLine) -> None:
    assert line.task is None


def test_a_progress_line_holds_the_task_given(of_task: ProgressLine) -> None:
    assert of_task.task == make_task_id(3)


def test_a_blank_progress_line_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^text is empty$"):
        make_progress_line(" ", ON)


def test_the_row_of_a_line_of_a_task_names_the_task(of_task: ProgressLine) -> None:
    assert progress_row(of_task) == ProgressRow(ON, "a text", "T-0003")


def test_the_row_of_a_line_of_the_work_item_names_no_task(line: ProgressLine) -> None:
    assert progress_row(line).task == ""


def test_two_lines_are_kept_in_the_order_noted() -> None:
    first = make_progress_line("the first", ON)
    second = make_progress_line("the second", ON)
    kept = progressed_work_item(progressed_work_item(BARE, first), second)
    assert kept.progress == (first, second)


def test_a_line_of_a_task_of_the_work_item_is_kept_on_it(of_task: ProgressLine) -> None:
    assert progressed_work_item(ITEM, of_task).progress == (of_task,)


def test_a_line_of_a_task_the_work_item_does_not_hold_is_refused() -> None:
    line = make_progress_line("a text", ON, make_task_id(9))
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0009 in the record$"):
        progressed_work_item(ITEM, line)


def test_a_progress_line_is_no_knowledge_line(line: ProgressLine) -> None:
    assert progressed_work_item(ITEM, line).knowledge == ()


@pytest.mark.parametrize(
    ("item", "move"),
    [
        (ITEM, lambda item: started_work_item(item, ON)),
        (HALF, lambda item: blocked_work_item(item, "no key", "developer", ON)),
        (STUCK, unblocked_work_item),
        (DONE, lambda item: completed_work_item(item, ON, COMMIT)),
        (BARE, lambda item: removed_work_item(item, "a reason", ON)),
        (BARE, lambda item: amended_work_item(item, Amendment(title="a new title"))),
    ],
    ids=["started", "blocked", "unblocked", "completed", "removed", "amended"],
)
def test_a_move_keeps_the_progress_lines_of_the_work_item(
    line: ProgressLine,
    item: WorkItemState,
    move: Callable[[WorkItemState], WorkItemState],
) -> None:
    assert move(progressed_work_item(item, line)).progress == (line,)
