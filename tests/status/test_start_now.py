"""The lines that can start now: the limit of the development, and the lines it leaves marked."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.record import Parallel, Unlimited
from flowgraph.record.layers import UNGATED, Development, Merge
from flowgraph.status.next import (
    NextOnly,
    NoLimit,
    Within,
    start_limit,
    start_now_ids,
    with_next,
    with_start_now,
)
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def row(item: str, waits_for: list[str] | None = None) -> WorkItemRow:
    """A work item in Backlog waiting for those ids."""
    return WorkItemRow(item, "a title", "backlog", created=CREATED, waits_for=waits_for or [])


def feature(item: str, held: int) -> FeatureRow:
    """A Feature in Backlog holding that many work items, its first waiting for nothing."""
    return FeatureRow(item, "a feature", "Backlog", 0, held)


def development(*, enabled: bool, parallel: Parallel | Unlimited) -> Development:
    """The development, on or off, with that limit."""
    return Development(enabled=enabled, parallel=parallel, merge=Merge.MERGE_COMMIT, gate=UNGATED)


FOUR = [row("S-0001"), row("S-0002", ["S-0004"]), row("S-0003"), row("S-0004")]


def test_the_development_off_limits_to_the_next_to_start_alone() -> None:
    assert start_limit(development(enabled=False, parallel=Parallel(3))) == NextOnly()


def test_the_development_on_without_a_limit_has_no_limit() -> None:
    assert start_limit(development(enabled=True, parallel=Unlimited())) == NoLimit()


def test_the_development_on_with_parallel_3_is_within_3() -> None:
    assert start_limit(development(enabled=True, parallel=Parallel(3))) == Within(3)


def test_next_only_marks_what_with_next_marks() -> None:
    assert with_start_now(FOUR, NextOnly(), 0) == with_next(FOUR)


def test_no_limit_marks_every_line_that_waits_for_nothing() -> None:
    assert start_now_ids(with_start_now(FOUR, NoLimit(), 2)) == ["S-0001", "S-0003", "S-0004"]


def test_within_marks_the_first_lines_the_places_left_by_those_started() -> None:
    assert start_now_ids(with_start_now(FOUR, Within(3), 1)) == ["S-0001", "S-0003"]


def test_within_skips_a_line_that_waits_and_goes_on_to_the_next() -> None:
    lines = [row("S-0001", ["S-0003"]), row("S-0002"), row("S-0003")]
    assert start_now_ids(with_start_now(lines, Within(2), 0)) == ["S-0002", "S-0003"]


def test_within_marks_none_when_as_many_are_started_as_the_limit() -> None:
    assert start_now_ids(with_start_now(FOUR, Within(2), 2)) == []


def test_within_marks_none_when_more_are_started_than_the_limit() -> None:
    assert start_now_ids(with_start_now(FOUR, Within(1), 3)) == []


def test_a_feature_that_can_start_takes_one_place() -> None:
    lines = [feature("F-0001", 3), row("S-0001")]
    assert start_now_ids(with_start_now(lines, Within(2), 0)) == ["F-0001", "S-0001"]


def test_a_feature_without_a_work_item_in_backlog_takes_no_place() -> None:
    assert start_now_ids(with_start_now([feature("F-0001", 0), row("S-0001")], NoLimit(), 0)) == [
        "S-0001"
    ]


def test_the_lines_are_given_back_in_the_order_given() -> None:
    assert [each.id for each in with_start_now(FOUR, Within(3), 0)] == [
        "S-0001",
        "S-0002",
        "S-0003",
        "S-0004",
    ]


def test_no_id_is_listed_for_lines_none_of_which_is_marked() -> None:
    assert start_now_ids(FOUR) == []
