"""The reorder of an item named by its id: a work item or a Feature put before another."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.feature import make_feature
from flowgraph.item.commands import ItemIdError, Store, Written, reorder_item
from flowgraph.parent import make_feature_id
from flowgraph.record.queue import NotInBacklogError, Queue, UnderFeatureError, make_queue
from flowgraph.record.store import FeatureStore
from flowgraph.story import STORY, make_story_id
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.command

DAY = {number: datetime(2026, 1, number, tzinfo=UTC) for number in range(1, 9)}
S1, S2, S3, S4, S5, S6, S7 = (make_story_id(number) for number in range(1, 8))
F1, F2 = make_feature_id(1), make_feature_id(2)
NO_QUEUE = make_queue([])


def never(*_: object) -> Never:
    """A read or a write that a reorder never asks for."""
    raise AssertionError("a reorder reads the rows, the Features and the queue, and saves it")


def story(number: int, state: str, parent: str = "") -> WorkItemRow:
    """The row of the Story of that number in that state, added on the day of its number."""
    added = DAY[number]
    started = added if state == "started" else None
    return WorkItemRow(
        f"S-000{number}", f"title {number}", state, parent=parent, created=added, started=started
    )


# A Story standing alone, a Feature in Backlog with two Stories, a Feature in progress with two
# Stories still in Backlog, and a last Story standing alone.
ROWS = [
    story(1, "backlog"),
    story(2, "backlog", "F-0001"),
    story(3, "backlog", "F-0001"),
    story(4, "started", "F-0002"),
    story(5, "backlog", "F-0002"),
    story(6, "backlog", "F-0002"),
    story(7, "backlog"),
]
FEATURES = [
    make_feature(F1, "feature 1", ["a criterion"], "", DAY[2]),
    make_feature(F2, "feature 2", ["a criterion"], "", DAY[4]),
]


def store(saved: list[Queue], queue: Queue = NO_QUEUE) -> Store:
    """The store of a record holding ROWS, FEATURES and that queue; it notes the queues it saves.

    As added its Backlog reads S-0001, F-0001, S-0007 by line, then S-0002, S-0003, S-0005 and
    S-0006 under their Features.
    """
    held = {each.id: each for each in FEATURES}
    return Store(
        find_work_item_rows=lambda kind: ROWS if kind == STORY else [],
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: queue,
        save_queue=saved.append,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(held.__getitem__, never, lambda: ["F-0002", "F-0001"]),
    )


def saved_by(item: str, before: str, queue: Queue = NO_QUEUE) -> list[Queue]:
    """The queues a reorder of the item before the other saves, from that queue."""
    saved: list[Queue] = []
    reorder_item(item, before, store(saved, queue))
    return saved


def test_a_feature_put_before_a_work_item_says_both_and_the_message_of_its_commit() -> None:
    assert reorder_item("F-0001", "S-0001", store([])) == Written(
        "moved F-0001 before S-0001\n", "chore: reorder F-0001 before S-0001 in the record"
    )


def test_a_work_item_put_before_a_feature_says_both_and_the_message_of_its_commit() -> None:
    assert reorder_item("S-0007", "F-0001", store([])) == Written(
        "moved S-0007 before F-0001\n", "chore: reorder S-0007 before F-0001 in the record"
    )


def test_a_reorder_places_the_lines_as_added_then_the_work_items_under_a_feature() -> None:
    assert saved_by("F-0001", "S-0001") == [make_queue([F1, S1, S7, S2, S3, S5, S6])]


def test_a_work_item_of_a_feature_in_progress_is_put_before_another_of_that_feature() -> None:
    assert saved_by("S-0006", "S-0005") == [make_queue([S1, F1, S7, S2, S3, S6, S5])]


def test_a_reorder_of_a_line_keeps_the_places_the_queue_gave_the_work_items_under_a_feature() -> (
    None
):
    held = make_queue([S7, S3, S2, S6, S5])
    assert saved_by("F-0001", "S-0007", held) == [make_queue([F1, S7, S3, S2, S6, S5, S1])]


def test_a_reorder_inside_a_feature_keeps_the_places_the_queue_gave_the_lines() -> None:
    held = make_queue([S7, F1, S3, S2, S1])
    assert saved_by("S-0002", "S-0003", held) == [make_queue([S7, F1, S2, S3, S1, S5, S6])]


@pytest.mark.parametrize(
    ("item", "before", "error", "why"),
    [
        ("F-0002", "S-0001", NotInBacklogError, "F-0002 is not in Backlog"),
        ("S-0001", "F-0009", NotInBacklogError, "F-0009 is not in Backlog"),
        (
            "S-0002",
            "S-0001",
            UnderFeatureError,
            "S-0002 is under F-0001: it is reordered among the work items of F-0001 alone",
        ),
        (
            "F-0001",
            "S-0005",
            UnderFeatureError,
            "S-0005 is under F-0002: it is reordered among the work items of F-0002 alone",
        ),
        ("T-0001", "S-0001", ItemIdError, "'T-0001' is no Story, Upkeep, Bug, Spike or Feature id"),
    ],
    ids=[
        "a-feature-in-progress",
        "before-a-feature-the-record-does-not-hold",
        "a-work-item-of-a-feature-before-one-standing-alone",
        "a-feature-before-a-work-item-of-another",
        "no-id",
    ],
)
def test_a_reorder_refused_names_why(
    item: str, before: str, error: type[Exception], why: str
) -> None:
    with pytest.raises(error, match=f"^{why}$"):
        reorder_item(item, before, store([]))


def test_a_reorder_refused_saves_nothing() -> None:
    saved: list[Queue] = []
    with pytest.raises(UnderFeatureError):
        reorder_item("S-0002", "S-0001", store(saved))
    assert saved == []
