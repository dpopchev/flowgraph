"""The completion of a work item under a Feature, and of the Feature with its last one."""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import NO_COMMIT, Evidence, make_commit, make_scenario
from flowgraph.development.scope import OutOfScopeError
from flowgraph.feature import (
    FeatureNotFoundError,
    FeatureState,
    completed_feature,
    make_feature,
    started_feature,
)
from flowgraph.feature.complete import complete_with_feature
from flowgraph.parent import STANDALONE, FeatureId, Parent, make_feature_id
from flowgraph.queue import make_queue
from flowgraph.store import NO_FEATURES, FeatureStore, Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import OpenTaskError, make_task, make_task_id
from flowgraph.work_item import (
    WorkItem,
    WorkItemId,
    WorkItemState,
    append_task,
    completed_task,
    completed_work_item,
    make_work_item,
    removed_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

DAY = {number: datetime(2026, 1, number, tzinfo=UTC) for number in range(1, 9)}
NOW = datetime(2026, 2, 1, 9, 0, 0, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
F1, F2 = make_feature_id(1), make_feature_id(2)
S2 = make_story_id(2)
FEATURE = make_feature(F1, "a feature title", ["a criterion"], "", DAY[1])
STARTED = started_feature(FEATURE, DAY[5])
COMPLETED = completed_feature(STARTED, DAY[6], NO_COMMIT)

# What a completion saved, in the order saved.
type Saved = list[FeatureState | WorkItemState]


def never(*_: object) -> Never:
    """A read or a write of the record that the completion of a work item never asks for."""
    raise AssertionError("a completion reads the rows, the work item and its Feature")


def story(number: int, parent: Parent = F1) -> WorkItem:
    """The Story of that number in Backlog, added on the day of its number, with one Task."""
    criterion = make_scenario("a state", "an action", "another")
    item = make_work_item(
        make_story_id(number), f"title {number}", criterion, "", DAY[number], parent
    )
    return append_task(item, make_task(make_task_id(number), "a task", "an output", "", DAY[1]))


def started(number: int, parent: Parent = F1) -> WorkItemState:
    """The Story of that number, started on the day after it was added, its Task started."""
    on = DAY[number + 1]
    return started_task(started_work_item(story(number, parent), on), make_task_id(number), on)


def ready(number: int, parent: Parent = F1) -> WorkItemState:
    """The Story of that number, started, its one Task completed."""
    return completed_task(started(number, parent), make_task_id(number), DAY[number + 1], COMMIT)


def completed(number: int, parent: Parent = F1) -> WorkItemState:
    """The Story of that number, completed on the day after it was added."""
    return completed_work_item(ready(number, parent), DAY[number + 1], NO_COMMIT)


def removed(number: int, parent: Parent = F1) -> WorkItemState:
    """The Story of that number, removed from the Backlog."""
    return removed_work_item(story(number, parent), "a reason", DAY[number + 1])


def refuse_feature(feature: FeatureState) -> Never:
    """The save of a Feature on the branch of a work item, which writes that work item alone."""
    raise OutOfScopeError("F-0001 is not written here")


def store(
    items: Sequence[WorkItemState],
    feature: FeatureState,
    saved: Saved,
    features: FeatureStore | None = None,
) -> Store:
    """The store of a record holding those Stories and that Feature; it notes what it saves."""
    held = {item.id: item for item in items}

    def load_feature(feature_id: FeatureId) -> FeatureState:
        if feature_id != feature.id:
            raise FeatureNotFoundError(feature_id)
        return feature

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
        features=features or FeatureStore(load_feature, saved.append, lambda: ["F-0001"]),
    )


def complete(
    items: Sequence[WorkItemState],
    feature: FeatureState = STARTED,
    *,
    item: WorkItemId = S2,
    commit: Evidence = COMMIT,
    features: FeatureStore | None = None,
) -> tuple[FeatureId | None, Saved]:
    """Complete the Story named on a record of those Stories; the Feature completed, the saves."""
    saved: Saved = []
    with_it = complete_with_feature(
        item, commit, None, store(items, feature, saved, features), lambda: NOW
    )
    return with_it, saved


def test_the_completion_of_the_last_work_item_of_a_started_feature_names_the_feature() -> None:
    with_it, _ = complete([completed(1), ready(2)])
    assert with_it == F1


@pytest.mark.parametrize("commit", [COMMIT, NO_COMMIT], ids=["in-a-commit", "without-a-commit"])
def test_the_feature_is_saved_completed_at_the_time_and_in_the_commit_of_its_last_work_item(
    commit: Evidence,
) -> None:
    _, saved = complete([completed(1), ready(2)], commit=commit)
    assert saved[0] == completed_feature(STARTED, NOW, commit)


def test_the_last_work_item_is_saved_completed_after_its_feature_and_nothing_else() -> None:
    _, saved = complete([completed(1), ready(2)])
    assert saved[1:] == [completed_work_item(ready(2), NOW, COMMIT)]


@pytest.mark.parametrize(
    "items",
    [
        [ready(2)],
        [completed(1), ready(2), removed(3)],
        [removed(1), ready(2)],
        [completed(1), ready(2), story(3, STANDALONE)],
        [completed(1), ready(2), story(3, F2)],
    ],
    ids=[
        "its-one-work-item",
        "the-others-completed-or-removed",
        "the-others-removed",
        "beside-one-in-backlog-standing-alone",
        "beside-one-in-backlog-of-another-feature",
    ],
)
def test_a_started_feature_is_completed_once_each_other_work_item_of_it_is_completed_or_removed(
    items: list[WorkItemState],
) -> None:
    with_it, _ = complete(items)
    assert with_it == F1


LEFT_STARTED = [
    ([story(1), ready(2)], STARTED),
    ([completed(1), ready(2), story(3)], STARTED),
    ([started(1), ready(2)], STARTED),
    ([completed(1), ready(2)], FEATURE),
    ([completed(1), ready(2)], COMPLETED),
]
LEFT = [
    "one-in-backlog",
    "one-in-backlog-beside-a-completed-one",
    "one-started",
    "a-feature-never-started",
    "a-feature-completed-already",
]


@pytest.mark.parametrize(("items", "feature"), LEFT_STARTED, ids=LEFT)
def test_a_completion_that_completes_no_feature_names_none(
    items: list[WorkItemState], feature: FeatureState
) -> None:
    with_it, _ = complete(items, feature)
    assert with_it is None


@pytest.mark.parametrize(("items", "feature"), LEFT_STARTED, ids=LEFT)
def test_a_completion_that_completes_no_feature_saves_the_work_item_alone(
    items: list[WorkItemState], feature: FeatureState
) -> None:
    _, saved = complete(items, feature)
    assert saved == [completed_work_item(ready(2), NOW, COMMIT)]


def test_a_work_item_standing_alone_is_completed_without_a_read_of_a_feature() -> None:
    _, saved = complete([ready(2, STANDALONE)], features=NO_FEATURES)
    assert saved == [completed_work_item(ready(2, STANDALONE), NOW, COMMIT)]


def test_a_completion_refused_saves_neither_the_work_item_nor_its_feature() -> None:
    saved: Saved = []
    with pytest.raises(OpenTaskError):
        complete_with_feature(S2, COMMIT, None, store([started(2)], STARTED, saved), lambda: NOW)
    assert saved == []


def test_a_feature_whose_save_is_refused_leaves_its_last_work_item_unsaved() -> None:
    saved: Saved = []
    features = FeatureStore(lambda _: STARTED, refuse_feature, lambda: ["F-0001"])
    with pytest.raises(OutOfScopeError):
        complete_with_feature(
            S2, COMMIT, None, store([ready(2)], STARTED, saved, features), lambda: NOW
        )
    assert saved == []
