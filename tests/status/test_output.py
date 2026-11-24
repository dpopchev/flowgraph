"""The output of status in the format asked for: the text cut to the width, or the document."""

import json
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.item.commands import Store, status_item
from flowgraph.record.queue import make_queue
from flowgraph.status.document import StatusFormatError
from flowgraph.status.next import NextOnly
from flowgraph.status.text import cut_lines
from flowgraph.status.tops import WHOLE, same_top
from flowgraph.status.view import status_output, watch_item
from flowgraph.story import STORY
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ROWS = [
    WorkItemRow(f"S-{number:04d}", "a long title of a Story", "backlog", created=CREATED)
    for number in range(1, 8)
]


def never(*_: object) -> Never:
    """A read or a write that listing the record never asks for."""
    raise AssertionError("status reads the rows and the queue only")


def store() -> Store:
    """The store of a record holding ROWS, seven Stories in Backlog, and no queue."""
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


def test_the_text_is_what_status_prints_cut_to_the_width() -> None:
    assert status_output(store(), same_top(3), "text", 10, NextOnly()) == cut_lines(
        status_item(store(), same_top(3)), 10
    )


def test_the_text_is_the_default_text_of_status_when_there_is_no_width() -> None:
    assert status_output(store(), WHOLE, "text", None, NextOnly()) == status_item(store())


def test_the_json_lists_every_item_whatever_the_top() -> None:
    document = json.loads(status_output(store(), same_top(3), "json", 10, NextOnly()))
    assert document["buckets"][0]["count"] == len(document["buckets"][0]["items"]) == 7


def test_the_json_is_not_cut_to_the_width() -> None:
    document = json.loads(status_output(store(), WHOLE, "json", 10, NextOnly()))
    assert document["buckets"][0]["items"][0]["title"] == "a long title of a Story"


def test_a_format_that_is_none_is_refused() -> None:
    with pytest.raises(StatusFormatError):
        status_output(store(), WHOLE, "xml", None, NextOnly())


def test_a_frame_with_the_backlog_named_alone_lists_its_heading_and_no_other() -> None:
    frame = watch_item(store(), WHOLE, NextOnly(), {"Backlog"})
    assert [line for line in frame.splitlines() if line.endswith(")")] == ["Backlog (7)"]
