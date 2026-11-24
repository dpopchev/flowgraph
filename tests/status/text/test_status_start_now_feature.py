"""The text of status for the work items that can start now under a started Feature."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import same_top, status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def story(item: int, *, marked: bool = False) -> WorkItemRow:
    """A Story in Backlog of that number, marked as able to start now or not."""
    return WorkItemRow(f"S-{item:04}", "a title", "backlog", created=CREATED, next_to_start=marked)


def feature(item: int, work_items: list[WorkItemRow], started: list[WorkItemRow]) -> FeatureRow:
    """A Feature in InProgress over those work items, those started listed under it."""
    return FeatureRow(
        f"F-{item:04}",
        "a feature",
        "in-progress",
        0,
        len(work_items),
        work_items=work_items,
        started=started,
        is_started=True,
    )


FIRST = replace(story(1), state="started")
WITH_TWO = feature(1, [FIRST, story(2, marked=True), story(3, marked=True)], [FIRST])


def progress(rows: list[FeatureRow]) -> list[str]:
    """The lines of the text between the heading of InProgress and that of Completed."""
    lines = status_text(rows).splitlines()
    return lines[lines.index("in-progress (1)") + 1 : lines.index("completed (0)")]


def test_each_marked_work_item_is_listed_under_its_feature_after_the_started_ones() -> None:
    assert progress([WITH_TWO])[1:] == [
        "    S-0001  0/0 T  a title",
        "  = S-0002  []  a title",
        "  = S-0003  []  a title",
    ]


def test_a_work_item_not_marked_is_not_listed_under_its_feature() -> None:
    plain = feature(1, [FIRST, story(2)], [FIRST])
    assert progress([plain])[1:] == ["    S-0001  0/0 T  a title"]


def test_the_feature_holding_a_marked_work_item_is_listed_after_the_top_that_leaves_it_out() -> (
    None
):
    plain = [feature(number, [story(number + 10)], []) for number in (2, 3)]
    lines = status_text([*plain, WITH_TWO], same_top(1)).splitlines()
    assert lines[lines.index("in-progress (3)") + 1 :][:5] == [
        "  F-0002  0/1 W  a feature",
        "  F-0001  0/3 W  a feature",
        "    S-0001  0/0 T  a title",
        "  = S-0002  []  a title",
        "  = S-0003  []  a title",
    ]
