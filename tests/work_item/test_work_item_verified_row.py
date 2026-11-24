"""The answer of the closing a work item row holds: as projected and as read from its file."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pytest

from flowgraph.criterion import NO_COMMIT, Criterion, make_scenario
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Kind,
    WorkItemState,
    append_task,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item_rows,
    started_task,
    started_work_item,
    verified_work_item,
    work_item_row,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, microsecond=500, tzinfo=UTC)
TEXT = "make check: all checks passed"
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)


def completed(kind: Kind, criterion: Criterion) -> WorkItemState:
    """A work item of that kind with one Task, started and completed."""
    made = make_work_item(make_work_item_id(kind, 1), "a title", criterion, "", CREATED)
    item = append_task(made, TASK)
    begun = started_task(started_work_item(item, ON), make_task_id(1), ON)
    done = completed_task(begun, make_task_id(1), ON, NO_COMMIT)
    return completed_work_item(done, ON, NO_COMMIT, None)


CHORE_DONE = completed(CHORE, make_scenario("a", "b", "c"))


@pytest.mark.model
def test_the_row_of_a_completed_work_item_with_no_answer_holds_none() -> None:
    assert work_item_row(CHORE_DONE).verified == ""


@pytest.mark.model
@pytest.mark.parametrize("answer", ["yes", "no"])
def test_the_row_of_a_verified_work_item_holds_the_answer(answer: Literal["yes", "no"]) -> None:
    item = verified_work_item(CHORE_DONE, TEXT, ON, answer)
    assert work_item_row(item).verified == answer


@pytest.mark.model
def test_the_row_of_a_started_work_item_holds_none() -> None:
    made = make_work_item(
        make_work_item_id(CHORE, 1), "a title", make_scenario("a", "b", "c"), "", CREATED
    )
    assert work_item_row(started_work_item(append_task(made, TASK), ON)).verified == ""


@pytest.mark.edge
def test_the_row_read_from_a_file_of_a_verified_work_item_is_the_row_projected(
    tmp_path: Path,
) -> None:
    item = verified_work_item(CHORE_DONE, TEXT, ON, "no")
    write_work_item(tmp_path, item)
    assert read_work_item_rows(tmp_path, CHORE) == [work_item_row(item)]


@pytest.mark.edge
def test_the_row_read_from_a_file_with_no_answer_is_the_row_projected(tmp_path: Path) -> None:
    write_work_item(tmp_path, CHORE_DONE)
    assert read_work_item_rows(tmp_path, CHORE) == [work_item_row(CHORE_DONE)]
