"""The top of the Backlog: the first line status marks, or the refusal naming why none is marked."""

import re
from dataclasses import replace
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.item.commands import Store
from flowgraph.record.queue import make_queue
from flowgraph.status.next import NextOnly, NoLimit
from flowgraph.status.top import EMPTY, NONE_MARKED, NothingToStartError, top_of, top_to_start
from flowgraph.story import STORY
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ROWS = [
    WorkItemRow(f"S-{number:04d}", "a long title of a Story", "backlog", created=CREATED)
    for number in range(1, 8)
]


def never(*_: object) -> Never:
    """A read or a write that listing the record never asks for."""
    raise AssertionError("the top reads the rows and the queue only")


def store() -> Store:
    """The store of a record holding ROWS, seven Stories in Backlog with no Task, and no queue."""
    return Store(
        find_work_item_rows=lambda kind: ROWS if kind == STORY else [],
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def row(item: str, waits_for: list[str] | None = None, *, tasks: int = 1) -> WorkItemRow:
    """A work item in Backlog waiting for those ids, holding that many Tasks."""
    return WorkItemRow(
        item,
        "a title",
        "backlog",
        created=CREATED,
        waits_for=waits_for or [],
        tasks=[TaskRow(f"T-{at:04}", "a task", "an output", "", "todo") for at in range(tasks)],
    )


def feature(item: str, held: int, work_items: list[WorkItemRow] | None = None) -> FeatureRow:
    """A Feature in Backlog holding that many work items."""
    return FeatureRow(item, "a feature", "backlog", 0, held, work_items=work_items or [])


def refusal(first: str) -> str:
    """The whole line of the refusal naming the first line of the Backlog, matched exactly."""
    return "^" + re.escape(NONE_MARKED.format(first=first)) + "$"


def empty() -> str:
    """The whole line of the refusal of an empty Backlog, matched exactly."""
    return "^" + re.escape(EMPTY) + "$"


def test_of_two_lines_the_second_marked_gives_its_id() -> None:
    rows = [row("S-0001"), replace(row("S-0002"), next_to_start=True)]
    assert top_of(rows) == "S-0002"


def test_of_two_lines_both_marked_gives_the_first() -> None:
    rows = [
        replace(row("S-0001"), next_to_start=True),
        replace(row("S-0002"), next_to_start=True),
    ]
    assert top_of(rows) == "S-0001"


def test_a_work_item_marked_under_a_started_feature_comes_before_a_marked_line() -> None:
    under = replace(row("S-0002"), next_to_start=True)
    started = replace(feature("F-0001", 2, [under]), bucket="in-progress", is_started=True)
    rows = [replace(row("S-0005"), next_to_start=True), started]
    assert top_of(rows) == "S-0002"


def test_no_mark_over_two_lines_in_backlog_names_the_first_line() -> None:
    with pytest.raises(NothingToStartError, match=refusal("S-0001")):
        top_of([row("S-0001"), row("S-0002")])


def test_a_feature_first_in_backlog_is_named_by_its_id() -> None:
    with pytest.raises(NothingToStartError, match=refusal("F-0001")):
        top_of([feature("F-0001", 2, [row("S-0001"), row("S-0002")])])


def test_no_row_raises_the_empty_backlog() -> None:
    with pytest.raises(NothingToStartError, match=empty()):
        top_of([])


def test_one_started_row_alone_raises_the_empty_backlog() -> None:
    with pytest.raises(NothingToStartError, match=empty()):
        top_of([replace(row("S-0001"), state="started")])


def test_the_top_of_the_store_under_next_only_is_the_first_story() -> None:
    assert top_to_start(store(), NextOnly()) == "S-0001"


def test_the_top_of_the_store_with_no_limit_names_the_first_story_when_none_is_planned() -> None:
    with pytest.raises(NothingToStartError, match=refusal("S-0001")):
        top_to_start(store(), NoLimit())
