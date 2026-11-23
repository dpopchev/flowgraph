"""The JSON document of status: `can_start` lists the lines marked, `next_to_start` the first."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.status.document import status_json
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def story(item: int, *, marked: bool = False) -> WorkItemRow:
    """A Story in Backlog of that number, marked as able to start now or not."""
    return WorkItemRow(f"S-{item:04}", "a title", "backlog", created=CREATED, next_to_start=marked)


def document(*rows: WorkItemRow) -> dict[str, Any]:
    """The document of the rows, parsed."""
    return json.loads(status_json(rows))


def test_can_start_lists_the_ids_marked_in_the_order_given() -> None:
    marked = document(story(1, marked=True), story(2), story(3, marked=True))
    assert marked["can_start"] == ["S-0001", "S-0003"]


def test_can_start_is_empty_when_no_line_is_marked() -> None:
    assert document(story(1), story(2))["can_start"] == []


def test_next_to_start_is_the_first_id_marked() -> None:
    marked = document(story(1), story(2, marked=True), story(3, marked=True))
    assert marked["next_to_start"] == "S-0002"


def test_next_to_start_is_null_when_no_line_is_marked() -> None:
    assert document(story(1))["next_to_start"] is None
