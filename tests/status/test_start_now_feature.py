"""The lines that can start now under a started Feature, ahead of the lines of the Backlog."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status.next import NextOnly, NoLimit, Within, start_now_ids, with_start_now
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def story(
    item: int, state: str = "backlog", waits_for: list[str] | None = None, *, tasks: int = 1
) -> WorkItemRow:
    """A Story in that state waiting for those ids, holding that many Tasks."""
    return WorkItemRow(
        f"S-{item:04}",
        "a title",
        state,
        created=CREATED,
        waits_for=waits_for or [],
        tasks=[TaskRow(f"T-{at:04}", "a task", "an output", "", "todo") for at in range(tasks)],
    )


def feature(
    item: int, work_items: list[WorkItemRow], *, started: bool = True, bucket: str = "InProgress"
) -> FeatureRow:
    """A Feature in that bucket holding those work items, started or not."""
    return FeatureRow(
        f"F-{item:04}",
        "a feature",
        bucket,
        0,
        len(work_items),
        work_items=work_items,
        is_started=started,
    )


def line(item: int) -> WorkItemRow:
    """A line of the Backlog: a Story that waits for nothing."""
    return story(item)


UNDER = [story(1, "started"), story(2), story(3), story(4)]


def test_each_work_item_in_backlog_under_a_started_feature_takes_a_place() -> None:
    marked = with_start_now([feature(1, UNDER)], Within(3), 1)
    assert start_now_ids(marked) == ["S-0002", "S-0003"]


def test_the_places_of_a_started_feature_come_before_the_lines_of_the_backlog() -> None:
    marked = with_start_now([line(9), feature(1, UNDER)], Within(3), 1)
    assert start_now_ids(marked) == ["S-0002", "S-0003"]


def test_a_line_of_the_backlog_takes_the_place_the_work_items_of_a_feature_leave() -> None:
    marked = with_start_now([line(9), feature(1, UNDER[:3])], Within(4), 1)
    assert start_now_ids(marked) == ["S-0002", "S-0003", "S-0009"]


def test_the_lines_marked_stay_in_the_rows_given() -> None:
    marked = with_start_now([line(9), feature(1, UNDER)], Within(4), 1)
    assert [row.id for row in marked] == ["S-0009", "F-0001"]


def test_the_work_items_of_the_first_started_feature_come_before_those_of_the_second() -> None:
    rows = [feature(2, [story(5)]), feature(1, [story(6)])]
    assert start_now_ids(with_start_now(rows, NoLimit(), 0)) == ["S-0005", "S-0006"]


def test_a_work_item_that_waits_takes_no_place() -> None:
    under = [story(1, waits_for=["S-0002"]), story(2)]
    assert start_now_ids(with_start_now([feature(1, under)], NoLimit(), 0)) == ["S-0002"]


def test_a_work_item_with_no_task_under_a_started_feature_takes_no_place_and_the_next_does() -> (
    None
):
    under = [story(1, tasks=0), story(2)]
    assert start_now_ids(with_start_now([feature(1, under)], Within(1), 0)) == ["S-0002"]


def test_a_started_work_item_is_not_marked() -> None:
    assert start_now_ids(with_start_now([feature(1, [story(1, "started")])], NoLimit(), 1)) == []


def test_a_blocked_feature_gives_no_place() -> None:
    blocked = feature(1, UNDER, started=False)
    assert start_now_ids(with_start_now([blocked], NoLimit(), 1)) == []


def test_a_feature_never_started_that_is_listed_in_progress_gives_no_place() -> None:
    never = feature(1, UNDER, started=False)
    assert start_now_ids(with_start_now([never], Within(3), 1)) == []


def test_a_feature_in_backlog_takes_one_place_through_its_first_work_item() -> None:
    backlog = FeatureRow("F-0002", "a feature", "Backlog", 0, 3, work_items=[story(7), story(8)])
    assert start_now_ids(with_start_now([backlog], Within(3), 0)) == ["F-0002"]


def test_the_limit_counts_the_work_items_started_under_a_feature() -> None:
    marked = with_start_now([feature(1, UNDER)], Within(2), 1)
    assert start_now_ids(marked) == ["S-0002"]


def test_with_the_development_off_nothing_under_a_feature_is_marked() -> None:
    assert start_now_ids(with_start_now([feature(1, UNDER)], NextOnly(), 1)) == []
