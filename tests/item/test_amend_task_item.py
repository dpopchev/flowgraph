"""The amend of a Task by its id: the parts an amend states are read as those of a Task."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.item.amend import amend_task_item
from flowgraph.item.commands import Written
from flowgraph.parent import STANDALONE
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import (
    StartedAlreadyError,
    TaskIdError,
    TaskNotFoundError,
    make_task,
    make_task_id,
    started,
)
from flowgraph.work_item import (
    Amendment,
    NoSuchPartError,
    WorkItemState,
    append_task,
    make_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
BEGUN = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)
FIRST = make_task(make_task_id(1), "a task", "an output", "", CREATED)
SECOND = make_task(make_task_id(2), "another task", "another output", "how", CREATED)
BARE = make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
STARTED = started_task(
    started_work_item(append_task(append_task(BARE, FIRST), SECOND), BEGUN),
    make_task_id(1),
    BEGUN,
)
ONLY_A_TASK = "a Task is amended by its title, its output, its check and its description"


def never(*_: object) -> Never:
    """A read or a write of the record that an amend of a Task never asks for."""
    raise AssertionError("an amend of a Task reads and saves the work items alone")


def store(saved: list[WorkItemState]) -> Store:
    """The store of a record holding the started Story, which notes what it saves."""
    return Store(
        find_work_item_rows=lambda kind: [work_item_row(STARTED)] if kind == STORY else [],
        load_work_item=lambda _: STARTED,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=saved.append,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def amended(parts: Amendment, criteria: Sequence[str] | None = None) -> list[WorkItemState]:
    """What the amend of T-0002 with those parts saves."""
    saved: list[WorkItemState] = []
    amend_task_item("T-0002", parts, criteria, store(saved))
    return saved


def test_the_amend_of_a_task_in_backlog_says_it_and_the_message_of_its_commit() -> None:
    written = amend_task_item("T-0002", Amendment(title="a new title"), None, store([]))
    assert written == Written(
        "amended T-0002 of S-0001\n", "chore: amend T-0002 of S-0001 in the record"
    )


def test_the_story_saved_holds_the_new_title_and_the_other_task_as_it_was() -> None:
    assert amended(Amendment(title="a new title")) == [
        replace(STARTED, tasks=(started(FIRST, BEGUN), replace(SECOND, title="a new title")))
    ]


def test_the_output_and_the_check_reach_the_task() -> None:
    saved = amended(Amendment(output="a new output", check="make lint"))
    assert saved[0].tasks[1] == replace(SECOND, expected_output="a new output", check="make lint")


@pytest.mark.parametrize(
    ("parts", "criteria", "named"),
    [
        (Amendment(given="a state"), None, "given"),
        (Amendment(parent=STANDALONE), None, "parent"),
        (Amendment(complexity="high"), None, "complexity"),
        (Amendment(depends_on=(make_story_id(2),)), None, "depends_on"),
        (Amendment(about=("a term",)), None, "about"),
        (Amendment(), ("a criterion",), "criteria"),
        (Amendment(title="a new title", given="a state", about=("a term",)), None, "given, about"),
    ],
    ids=["given", "parent", "complexity", "depends_on", "about", "criteria", "beside-a-title"],
)
def test_a_part_that_is_no_part_of_a_task_is_refused_naming_it(
    parts: Amendment, criteria: Sequence[str] | None, named: str
) -> None:
    with pytest.raises(NoSuchPartError, match=rf"^T-0002 has no {named}: {ONLY_A_TASK}$"):
        amend_task_item("T-0002", parts, criteria, store([]))


def test_an_amend_refused_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(StartedAlreadyError):
        amend_task_item("T-0001", Amendment(title="a new title"), None, store(saved))
    assert saved == []


def test_a_task_the_record_does_not_hold_is_not_amended() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0009 in the record$"):
        amend_task_item("T-0009", Amendment(title="a new title"), None, store([]))


def test_a_task_id_below_one_is_refused() -> None:
    with pytest.raises(TaskIdError):
        amend_task_item("T-0000", Amendment(title="a new title"), None, store([]))
