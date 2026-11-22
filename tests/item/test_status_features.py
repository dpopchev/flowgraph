"""The Features of status: each one line in its bucket, in place of its work items."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_commit
from flowgraph.feature import (
    Feature,
    FeatureState,
    completed_feature,
    make_feature,
    started_feature,
)
from flowgraph.item import Store, status_item
from flowgraph.parent import make_feature_id
from flowgraph.queue import Queue, make_queue
from flowgraph.store import FeatureStore
from flowgraph.story import STORY, make_story_id
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

DAY = {number: datetime(2026, 1, number, tzinfo=UTC) for number in range(1, 8)}
NO_QUEUE = make_queue([])


def never(*_: object) -> Never:
    """A read or a write that listing the record never asks for."""
    raise AssertionError("status reads the rows, the queue and the Features only")


def feature(number: int, created: datetime = DAY[1]) -> Feature:
    """The Feature of that number, added at that time."""
    return make_feature(make_feature_id(number), f"feature {number}", ["a criterion"], "", created)


def story(
    number: int,
    state: str,
    parent: str = "",
    *,
    created: datetime = DAY[1],
    started: datetime | None = None,
    completed: datetime | None = None,
) -> WorkItemRow:
    """The row of the Story of that number in that state, under the Feature named if any."""
    return WorkItemRow(
        f"S-000{number}",
        f"title {number}",
        state,
        "abc1234" if state == "completed" else "",
        "a reason" if state == "removed" else "",
        parent,
        created=created,
        started=started,
        completed=completed,
    )


def store(
    rows: Sequence[WorkItemRow], features: Sequence[FeatureState], queue: Queue = NO_QUEUE
) -> Store:
    """The store of a record holding those Stories, those Features and that queue.

    The ids of the Features are listed the last first, as files in no order.
    """
    held = {each.id: each for each in features}
    return Store(
        find_work_item_rows=lambda kind: list(rows) if kind == STORY else [],
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: queue,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(
            held.__getitem__, never, lambda: [f"F-000{each.number}" for each in reversed(held)]
        ),
    )


IN_BACKLOG = [
    story(1, "backlog"),
    story(2, "backlog", "F-0001", created=DAY[3]),
    story(3, "backlog", created=DAY[4]),
]


def test_a_feature_in_backlog_is_listed_after_what_was_added_before_it_and_not_its_work_items() -> (
    None
):
    assert status_item(store(IN_BACKLOG, [feature(1, DAY[2])])) == (
        "Backlog (3)\n"
        "  S-0001  title 1\n"
        "  F-0001  0/1 W  feature 1\n"
        "  S-0003  title 3\n"
        "InProgress (0)\n"
        "Completed (0)\n"
    )


def test_a_feature_never_placed_is_listed_after_the_work_items_placed_in_the_queue() -> None:
    placed = make_queue([make_story_id(3)])
    assert status_item(store(IN_BACKLOG, [feature(1, DAY[2])], placed)).splitlines()[1:4] == [
        "  S-0003  title 3",
        "  S-0001  title 1",
        "  F-0001  0/1 W  feature 1",
    ]


def test_a_feature_placed_in_the_queue_is_listed_at_its_place_among_the_placed_work_items() -> None:
    placed = make_queue([make_feature_id(1), make_story_id(3)])
    assert status_item(store(IN_BACKLOG, [feature(1, DAY[2])], placed)).splitlines()[1:4] == [
        "  F-0001  0/1 W  feature 1",
        "  S-0003  title 3",
        "  S-0001  title 1",
    ]


def test_a_work_item_under_a_feature_placed_in_the_queue_is_listed_on_no_line() -> None:
    placed = make_queue([make_story_id(2), make_story_id(3)])
    assert status_item(store(IN_BACKLOG, [feature(1, DAY[2])], placed)).splitlines()[1:4] == [
        "  S-0003  title 3",
        "  S-0001  title 1",
        "  F-0001  0/1 W  feature 1",
    ]


def test_a_work_item_under_a_feature_the_record_does_not_hold_is_listed_in_its_bucket() -> None:
    rows = [
        story(1, "backlog", "F-0009"),
        story(2, "started", "F-0009", started=DAY[2]),
        story(3, "completed", "F-0009", completed=DAY[3]),
    ]
    assert status_item(store(rows, [])) == (
        "Backlog (1)\n"
        "  S-0001  title 1\n"
        "InProgress (1)\n"
        "  S-0002  0/0 T  title 2\n"
        "Completed (1)\n"
        "  S-0003  abc1234  title 3\n"
    )


def test_a_feature_placed_in_the_queue_that_left_the_backlog_is_listed_once_under_its_bucket() -> (
    None
):
    rows = [story(1, "backlog"), story(2, "started", "F-0001", started=DAY[2])]
    placed = make_queue([make_feature_id(1), make_story_id(1)])
    assert status_item(store(rows, [feature(1)], placed)) == (
        "Backlog (1)\n"
        "  S-0001  title 1\n"
        "InProgress (1)\n"
        "  F-0001  0/1 W  feature 1\n"
        "    S-0002  0/0 T  title 2\n"
        "Completed (0)\n"
    )


def test_a_started_feature_is_listed_under_in_progress_though_no_work_item_of_it_is_begun() -> None:
    rows = [story(1, "backlog", "F-0001")]
    assert status_item(store(rows, [started_feature(feature(1), DAY[2])])) == (
        "Backlog (0)\nInProgress (1)\n  F-0001  0/1 W  feature 1\nCompleted (0)\n"
    )


def test_a_feature_added_at_the_time_of_a_work_item_is_listed_after_it() -> None:
    assert status_item(store([story(1, "backlog")], [feature(1)])).splitlines()[1:3] == [
        "  S-0001  title 1",
        "  F-0001  0/0 W  feature 1",
    ]


def test_features_added_at_one_time_are_listed_by_number() -> None:
    assert status_item(store([], [feature(1), feature(2)])).splitlines()[1:3] == [
        "  F-0001  0/0 W  feature 1",
        "  F-0002  0/0 W  feature 2",
    ]


def test_a_feature_in_progress_is_placed_by_its_last_started_work_item_listed_under_it() -> None:
    rows = [
        story(1, "started", started=DAY[3]),
        story(2, "started", "F-0001", started=DAY[2]),
        story(3, "started", "F-0001", started=DAY[4]),
        story(4, "backlog", "F-0001"),
        story(5, "completed", "F-0001", completed=DAY[7]),
        story(6, "started", started=DAY[5]),
    ]
    assert status_item(store(rows, [feature(1)])) == (
        "Backlog (0)\n"
        "InProgress (3)\n"
        "  S-0006  0/0 T  title 6\n"
        "  F-0001  1/4 W  feature 1\n"
        "    S-0003  0/0 T  title 3\n"
        "    S-0002  0/0 T  title 2\n"
        "  S-0001  0/0 T  title 1\n"
        "Completed (0)\n"
    )


def test_a_feature_in_progress_with_no_started_work_item_is_placed_by_its_last_completed_one() -> (
    None
):
    rows = [
        story(1, "started", started=DAY[3]),
        story(2, "completed", "F-0001", completed=DAY[4]),
        story(3, "backlog", "F-0001"),
        story(4, "started", started=DAY[5]),
    ]
    assert status_item(store(rows, [feature(1)])).splitlines()[2:5] == [
        "  S-0004  0/0 T  title 4",
        "  F-0001  1/2 W  feature 1",
        "  S-0001  0/0 T  title 1",
    ]


def test_a_completed_feature_is_placed_by_its_last_completed_work_item_and_lists_none_of_them() -> (
    None
):
    rows = [
        story(1, "completed", completed=DAY[3]),
        story(2, "completed", "F-0001", completed=DAY[2]),
        story(3, "completed", "F-0001", completed=DAY[4]),
        story(4, "completed", completed=DAY[5]),
    ]
    assert status_item(store(rows, [feature(1)])).splitlines()[2:] == [
        "Completed (3)",
        "  S-0004  abc1234  title 4",
        "  F-0001  2/2 W  feature 1",
        "  S-0001  abc1234  title 1",
    ]


def test_a_feature_completed_by_its_own_state_is_placed_by_its_completed_time_with_its_commit() -> (
    None
):
    rows = [
        story(1, "completed", completed=DAY[3]),
        story(2, "completed", "F-0001", completed=DAY[2]),
        story(3, "completed", completed=DAY[5]),
    ]
    landed = completed_feature(started_feature(feature(1), DAY[1]), DAY[4], make_commit("def5678"))
    assert status_item(store(rows, [landed])).splitlines()[2:] == [
        "Completed (3)",
        "  S-0003  abc1234  title 3",
        "  F-0001  1/1 W  def5678  feature 1",
        "  S-0001  abc1234  title 1",
    ]


def test_a_started_feature_whose_work_items_are_all_completed_or_removed_stays_in_progress() -> (
    None
):
    rows = [story(1, "completed", "F-0001", completed=DAY[3]), story(2, "removed", "F-0001")]
    assert status_item(store(rows, [started_feature(feature(1), DAY[2])])) == (
        "Backlog (0)\n"
        "InProgress (1)\n"
        "  F-0001  1/1 W  feature 1\n"
        "Completed (0)\n"
        "Removed (1)\n"
        "  S-0002  title 2  -- a reason\n"
    )


def test_a_removed_work_item_of_a_feature_keeps_its_line_under_removed() -> None:
    rows = [story(1, "removed", "F-0001"), story(2, "backlog", "F-0001")]
    assert status_item(store(rows, [feature(1)])) == (
        "Backlog (1)\n"
        "  F-0001  0/1 W  feature 1\n"
        "InProgress (0)\n"
        "Completed (0)\n"
        "Removed (1)\n"
        "  S-0001  title 1  -- a reason\n"
    )


def test_a_feature_with_every_work_item_removed_is_placed_in_completed_as_it_was_added() -> None:
    rows = [
        story(1, "completed", completed=DAY[2]),
        story(2, "removed", "F-0001"),
        story(3, "completed", completed=DAY[4]),
    ]
    assert status_item(store(rows, [feature(1, DAY[3])])).splitlines()[3:6] == [
        "  S-0003  abc1234  title 3",
        "  F-0001  0/0 W  feature 1",
        "  S-0001  abc1234  title 1",
    ]
