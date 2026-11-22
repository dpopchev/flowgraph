"""What a work item in Backlog waits for: the ids it depends on that are not completed."""

from datetime import UTC, datetime

import pytest

from flowgraph.status.waits import waits_for, with_waits
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def row(item: str, state: str, depends_on: list[str] | None = None) -> WorkItemRow:
    """A work item in that state depending on those ids."""
    return WorkItemRow(item, "a title", state, created=CREATED, depends_on=depends_on or [])


def record(*rows: WorkItemRow) -> dict[str, WorkItemRow]:
    """The rows under their ids."""
    return {each.id: each for each in rows}


def test_a_work_item_in_backlog_waits_for_the_one_it_depends_on_that_is_not_completed() -> None:
    held = record(row("S-0001", "started"), row("S-0002", "backlog", ["S-0001"]))
    assert waits_for(held["S-0002"], held) == ["S-0001"]


def test_a_work_item_waits_for_each_one_not_completed_in_the_order_written() -> None:
    held = record(
        row("S-0001", "backlog"),
        row("S-0002", "completed"),
        row("S-0003", "removed"),
        row("S-0004", "backlog", ["S-0003", "S-0002", "S-0001"]),
    )
    assert waits_for(held["S-0004"], held) == ["S-0003", "S-0001"]


def test_a_work_item_waits_for_nothing_once_each_one_it_depends_on_is_completed() -> None:
    held = record(row("S-0001", "completed"), row("S-0002", "backlog", ["S-0001"]))
    assert waits_for(held["S-0002"], held) == []


def test_a_started_work_item_waits_for_nothing() -> None:
    held = record(row("S-0001", "backlog"), row("S-0002", "started", ["S-0001"]))
    assert waits_for(held["S-0002"], held) == []


def test_a_work_item_waits_for_nothing_the_record_does_not_hold() -> None:
    held = record(row("S-0002", "backlog", ["S-0009"]))
    assert waits_for(held["S-0002"], held) == []


def test_every_row_is_given_back_under_its_key_with_what_it_waits_for() -> None:
    held = {
        1: row("S-0001", "backlog"),
        2: row("S-0002", "backlog", ["S-0001"]),
    }
    assert {key: each.waits_for for key, each in with_waits(held).items()} == {
        1: [],
        2: ["S-0001"],
    }
