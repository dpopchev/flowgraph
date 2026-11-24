"""The next to start: the first line of the Backlog that its start would take."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status.next import with_next
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def row(item: str, waits_for: list[str] | None = None) -> WorkItemRow:
    """A work item in Backlog waiting for those ids."""
    return WorkItemRow(item, "a title", "backlog", created=CREATED, waits_for=waits_for or [])


def feature(item: str, held: int, waits_for: list[str] | None = None) -> FeatureRow:
    """A Feature in Backlog holding that many work items, its first waiting for those ids."""
    return FeatureRow(item, "a feature", "backlog", 0, held, waits_for=waits_for or [])


def named(lines: list[WorkItemRow | FeatureRow]) -> list[str]:
    """The ids of the lines marked as the next to start."""
    return [each.id for each in lines if each.next_to_start]


def test_the_first_line_that_waits_for_nothing_is_the_next_to_start() -> None:
    lines = with_next([row("S-0001", ["S-0003"]), row("S-0002"), row("S-0003")])
    assert named(lines) == ["S-0002"]


def test_the_first_line_is_the_next_to_start_when_it_waits_for_nothing() -> None:
    assert named(with_next([row("S-0001"), row("S-0002")])) == ["S-0001"]


def test_no_line_is_the_next_to_start_when_each_one_waits() -> None:
    assert named(with_next([row("S-0001", ["S-0002"]), row("S-0002", ["S-0001"])])) == []


def test_a_feature_whose_first_work_item_waits_for_nothing_is_the_next_to_start() -> None:
    assert named(with_next([row("S-0001", ["S-0003"]), feature("F-0001", 2)])) == ["F-0001"]


def test_a_feature_whose_first_work_item_waits_is_not_the_next_to_start() -> None:
    assert named(with_next([feature("F-0001", 2, ["S-0009"]), row("S-0001")])) == ["S-0001"]


def test_a_feature_without_a_work_item_in_backlog_is_not_the_next_to_start() -> None:
    assert named(with_next([feature("F-0001", 0), row("S-0001")])) == ["S-0001"]


def test_the_lines_are_given_back_in_the_order_given() -> None:
    given = [row("S-0001", ["S-0002"]), row("S-0002")]
    assert [each.id for each in with_next(given)] == ["S-0001", "S-0002"]
