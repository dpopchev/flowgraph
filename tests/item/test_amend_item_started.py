"""The amend of a started work item by its id: the deviation is kept in the one save."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.item.commands import Written, amend_item
from flowgraph.knowledge import DEVIATION, make_knowledge_line
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Amendment,
    DeviationError,
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
TASK = make_task(make_task_id(1), "a task", "an output", "", CREATED)
STORY_ITEM = append_task(
    make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED), TASK
)
STARTED = started_task(started_work_item(STORY_ITEM, BEGUN), make_task_id(1), BEGUN)
LINE = make_knowledge_line(DEVIATION, "the title is narrowed", BEGUN)
TITLE = Amendment(title="another title")


def never(*_: object) -> Never:
    """A read or a write of the record that an amend never asks for."""
    raise AssertionError("an amend of a title reads and saves the work items alone")


def store(items: Sequence[WorkItemState], saved: list[WorkItemState]) -> Store:
    """The store of a record holding those Stories, which notes what it saves."""
    held = {item.id: item for item in items}
    return Store(
        find_work_item_rows=lambda kind: (
            [work_item_row(item) for item in items] if kind == STORY else []
        ),
        load_work_item=held.__getitem__,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=saved.append,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def test_a_started_story_amended_with_its_deviation_is_saved_once_with_both() -> None:
    saved: list[WorkItemState] = []
    amend_item("S-0001", TITLE, store([STARTED], saved), LINE)
    assert saved == [replace(STARTED, title="another title", knowledge=(LINE,))]


def test_a_started_story_amended_with_its_deviation_says_its_id_and_its_commit() -> None:
    written = amend_item("S-0001", TITLE, store([STARTED], []), LINE)
    assert written == Written("amended S-0001\n", "chore: amend S-0001 in the record")


def test_a_started_story_amended_without_a_deviation_is_refused_and_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(DeviationError):
        amend_item("S-0001", TITLE, store([STARTED], saved))
    assert saved == []
