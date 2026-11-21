"""The Features of status: listed by number, each with the bucket its work items derive."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.feature import Feature, make_feature
from flowgraph.item import Store, status_item
from flowgraph.parent import FeatureId, make_feature_id
from flowgraph.queue import make_queue
from flowgraph.store import FeatureStore
from flowgraph.story import STORY
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
FEATURES = {
    make_feature_id(number): make_feature(
        make_feature_id(number), title, ["a criterion"], "", CREATED
    )
    for number, title in [(1, "a feature title"), (2, "another feature title")]
}
ROWS = [
    WorkItemRow("ST-0001", "a story", "started", parent="F-0001", created=CREATED),
    WorkItemRow("ST-0002", "another story", "backlog", parent="F-0001", created=CREATED),
    WorkItemRow(
        "ST-0003", "a done story", "completed", "abc1234", parent="F-0002", created=CREATED
    ),
    WorkItemRow("ST-0004", "a story that stands alone", "started", created=CREATED),
]


def never(*_: object) -> Never:
    """A read or a write that listing the record never asks for."""
    raise AssertionError("status reads the rows, the queue and the Features only")


def held(feature_id: FeatureId) -> Feature:
    """The Feature of that id among FEATURES."""
    return FEATURES[feature_id]


def store(feature_ids: list[str]) -> Store:
    """The store of a record holding ROWS and the Features of those ids, as their files list."""
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
        features=FeatureStore(held, never, lambda: feature_ids),
    )


def test_the_features_are_listed_by_number_each_with_the_bucket_of_its_work_items() -> None:
    assert status_item(store(["F-0002", "F-0001"])).splitlines()[:3] == [
        "Features (2)",
        "  F-0001  0/2 W  InProgress  a feature title",
        "  F-0002  1/1 W  Completed  another feature title",
    ]


def test_the_work_items_are_listed_in_their_buckets_as_without_a_feature() -> None:
    assert (
        status_item(store(["F-0001", "F-0002"])).splitlines()[3:]
        == status_item(store([])).splitlines()
    )
