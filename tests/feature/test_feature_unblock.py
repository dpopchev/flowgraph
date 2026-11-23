"""The unblock of a Feature: it starts its next work item only while none of it is in progress."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.feature import (
    FeatureNotFoundError,
    FeatureState,
    blocked_feature,
    make_feature,
    started_feature,
)
from flowgraph.feature.block import unblock_named
from flowgraph.item.commands import Written
from flowgraph.parent import FeatureId, make_feature_id
from flowgraph.record import make_config
from flowgraph.record.queue import make_queue
from flowgraph.record.store import FeatureStore, Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItem,
    WorkItemState,
    append_task,
    blocked_work_item,
    make_work_item,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
F1 = make_feature_id(1)
BLOCKED = blocked_feature(
    started_feature(make_feature(F1, "a feature", ["a criterion"], "", CREATED), CREATED),
    "no budget",
    "a sponsor",
    CREATED,
)


def never(*_: object) -> Never:
    """A read or a write of the record that the unblock of a Feature never asks for."""
    raise AssertionError("an unblock reads the Feature, the rows and the queue")


def story(number: int) -> WorkItem:
    """The Story of that number in Backlog under F-0001, with one Task."""
    criterion = make_scenario("a state", "an action", "another")
    item = make_work_item(make_story_id(number), f"title {number}", criterion, "", CREATED, F1)
    return append_task(item, make_task(make_task_id(number), "a task", "an output", "", CREATED))


def store(items: Sequence[WorkItemState], saved: list[WorkItemState]) -> Store:
    """The store of a record holding those Stories and F-0001, which loads the Feature saved."""
    held = {item.id: item for item in items}
    features: list[FeatureState] = [BLOCKED]

    def load_feature(feature_id: FeatureId) -> FeatureState:
        if feature_id != F1:
            raise FeatureNotFoundError(feature_id)
        return features[-1]

    return Store(
        find_work_item_rows=lambda kind: (
            [work_item_row(item) for item in items] if kind == STORY else []
        ),
        load_work_item=held.__getitem__,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=saved.append,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(load_feature, features.append, lambda: ["F-0001"]),
    )


def test_the_unblock_of_a_feature_whose_work_item_in_progress_is_blocked_starts_none() -> None:
    held = blocked_work_item(started_work_item(story(1), CREATED), "no key", "developer", CREATED)
    saved: list[WorkItemState] = []
    written = unblock_named("F-0001", store([held, story(2)], saved), lambda: NOW, make_config(""))
    assert (written, saved) == (
        Written("unblocked F-0001\n", "chore: unblock F-0001 in the record"),
        [],
    )
