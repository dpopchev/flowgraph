"""The next work item of a started Feature, started by the completion of the one before."""

from collections.abc import Collection, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.development import make_slug
from flowgraph.development.scope import OutOfScopeError
from flowgraph.feature import FeatureState, completed_feature, make_feature, started_feature
from flowgraph.feature.next import complete_and_start_next
from flowgraph.item.commands import ToBranch, Written
from flowgraph.parent import STANDALONE, FeatureId, Parent, make_feature_id
from flowgraph.record import Config, make_config
from flowgraph.record.queue import Queue, make_queue
from flowgraph.record.store import FeatureStore, Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import make_task, make_task_id
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
NOW = datetime(2026, 2, 1, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
F1 = make_feature_id(1)
S2, S3 = make_story_id(2), make_story_id(3)
FEATURE = make_feature(F1, "a feature title", ["a criterion"], "", DAY[1])
STARTED = started_feature(FEATURE, DAY[5])
NO_QUEUE = make_queue([])
UNLIMITED = make_config("")
ONE_AT_ONCE = make_config("[development]\nenabled = true\nparallel = 1\n")
COMPLETED_ALONE = "completed S-0001 at abc1234\n"


def never(*_: object) -> Never:
    """A read or a write of the record that a completion never asks for."""
    raise AssertionError("a completion reads the rows, the queue, the work items and the Feature")


def story(number: int, parent: Parent = F1, *, tasks: int = 1) -> WorkItem:
    """The Story of that number in Backlog, added on the day of its number, with that many Tasks."""
    criterion = make_scenario("a state", "an action", "another")
    item = make_work_item(
        make_story_id(number), f"title {number}", criterion, "", DAY[number], parent
    )
    for _ in range(tasks):
        task = make_task(make_task_id(number), "a task title", "an output", "", DAY[number])
        item = append_task(item, task)
    return item


def started(number: int, parent: Parent = F1) -> WorkItemState:
    """The Story of that number, started on the day after it was added, its Task started."""
    on = DAY[number + 1]
    return started_task(started_work_item(story(number, parent), on), make_task_id(number), on)


def ready(number: int, parent: Parent = F1) -> WorkItemState:
    """The Story of that number, started, its one Task completed."""
    return completed_task(started(number, parent), make_task_id(number), DAY[number + 1], COMMIT)


def removed(number: int) -> WorkItemState:
    """The Story of that number, removed from the Backlog."""
    return removed_work_item(story(number), "a reason", DAY[number + 1])


def store(
    items: Sequence[WorkItemState],
    feature: FeatureState,
    queue: Queue,
    saved: list[WorkItemState],
    out_of_scope: Collection[WorkItemId],
) -> Store:
    """The store of a record holding those Stories, that Feature and that queue.

    It reads back what it saved and notes the work items saved, in the order saved; the save of
    a work item out of scope is refused, as on the branch of another work item.
    """
    held = {item.id: item for item in items}
    features = {feature.id: feature}

    def save_work_item(item: WorkItemState) -> None:
        if item.id in out_of_scope:
            raise OutOfScopeError("S-0002 is not written here")
        held[item.id] = item
        saved.append(item)

    def save_feature(saved_feature: FeatureState) -> None:
        features[saved_feature.id] = saved_feature

    def load_feature(feature_id: FeatureId) -> FeatureState:
        return features[feature_id]

    return Store(
        find_work_item_rows=lambda kind: (
            [work_item_row(item) for item in held.values()] if kind == STORY else []
        ),
        load_work_item=held.__getitem__,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=save_work_item,
        load_queue=lambda: queue,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(load_feature, save_feature, lambda: ["F-0001"]),
    )


def complete(
    items: Sequence[WorkItemState],
    feature: FeatureState = STARTED,
    queue: Queue = NO_QUEUE,
    *,
    item: str = "S-0001",
    config: Config = UNLIMITED,
    out_of_scope: Collection[WorkItemId] = (),
) -> tuple[Written, list[WorkItemState]]:
    """Complete the item named on a record of those Stories; what it says and what it saved."""
    saved: list[WorkItemState] = []
    held = store(items, feature, queue, saved, out_of_scope)
    written = complete_and_start_next(item, "abc1234", held, lambda: NOW, config)
    return written, saved


def test_the_completion_of_a_work_item_of_a_started_feature_names_the_next_started() -> None:
    written, _ = complete([ready(1), story(2)])
    assert written.out == f"{COMPLETED_ALONE}started S-0002\n"


def test_the_message_of_its_commit_names_the_completion_and_the_start() -> None:
    written, _ = complete([ready(1), story(2)])
    assert written.message == "chore: complete S-0001 and start S-0002 in the record"


def test_it_names_the_branch_of_the_next_work_item_by_the_slug_of_its_title() -> None:
    written, _ = complete([ready(1), story(2)])
    assert written.branch == ToBranch(S2, make_slug("title-2"))


def test_the_next_work_item_is_saved_started_after_the_completed_one() -> None:
    _, saved = complete([ready(1), story(2)])
    assert saved == [
        completed_work_item(ready(1), NOW, COMMIT),
        started_work_item(story(2), NOW),
    ]


def test_the_next_work_item_is_the_first_in_backlog_in_the_order_of_the_queue() -> None:
    written, _ = complete([ready(1), story(2), story(3)], queue=make_queue([S3, S2]))
    assert written.out == f"{COMPLETED_ALONE}started S-0003\n"


NOT_STARTED = [
    ([ready(1), story(2, tasks=0)], UNLIMITED, (), "S-0002 has no Task to start with"),
    (
        [ready(1), story(2), started(3, STANDALONE)],
        ONE_AT_ONCE,
        (),
        "S-0002 cannot start: development.parallel = 1, started already: S-0003",
    ),
    (
        [ready(1), story(2), started(3)],
        UNLIMITED,
        (),
        "S-0002 cannot start: F-0001 starts one work item at a time, started already: S-0003",
    ),
    ([ready(1), story(2)], UNLIMITED, (S2,), "S-0002 is not written here"),
    (
        [ready(1), replace(story(2), title="--")],
        UNLIMITED,
        (),
        "'' is no slug: it is lower-case letters and digits joined by hyphens",
    ),
]
WHY_NOT = [
    "without-a-task",
    "beside-as-many-as-parallel-starts",
    "beside-a-started-one-of-its-feature",
    "out-of-the-scope-of-the-branch",
    "a-title-that-gives-no-slug",
]


@pytest.mark.parametrize(("items", "config", "out_of_scope", "why"), NOT_STARTED, ids=WHY_NOT)
def test_a_next_work_item_that_cannot_start_is_named_not_started_after_the_completion(
    items: list[WorkItemState], config: Config, out_of_scope: Collection[WorkItemId], why: str
) -> None:
    written, _ = complete(items, config=config, out_of_scope=out_of_scope)
    assert written.out == f"{COMPLETED_ALONE}not started: {why}\n"


@pytest.mark.parametrize(("items", "config", "out_of_scope", "why"), NOT_STARTED, ids=WHY_NOT)
def test_a_next_work_item_that_cannot_start_leaves_the_completion_saved_alone(
    items: list[WorkItemState], config: Config, out_of_scope: Collection[WorkItemId], why: str
) -> None:
    _, saved = complete(items, config=config, out_of_scope=out_of_scope)
    assert saved == [completed_work_item(ready(1), NOW, COMMIT)]


@pytest.mark.parametrize(("items", "config", "out_of_scope", "why"), NOT_STARTED, ids=WHY_NOT)
def test_a_next_work_item_that_cannot_start_leaves_the_message_and_no_branch_of_the_completion(
    items: list[WorkItemState], config: Config, out_of_scope: Collection[WorkItemId], why: str
) -> None:
    written, _ = complete(items, config=config, out_of_scope=out_of_scope)
    assert (written.message, written.branch) == ("chore: complete S-0001 in the record", None)


@pytest.mark.parametrize(
    ("items", "feature", "item", "said"),
    [
        ([ready(1, STANDALONE), story(2)], STARTED, "S-0001", COMPLETED_ALONE),
        ([ready(1), story(2)], FEATURE, "S-0001", COMPLETED_ALONE),
        (
            [ready(1), story(2)],
            completed_feature(STARTED, DAY[6], COMMIT),
            "S-0001",
            COMPLETED_ALONE,
        ),
        (
            [ready(1), removed(2)],
            STARTED,
            "S-0001",
            f"{COMPLETED_ALONE}completed F-0001 at abc1234\n",
        ),
        ([started(1), story(2)], STARTED, "T-0001", "completed T-0001 of S-0001 at abc1234\n"),
    ],
    ids=[
        "a-work-item-standing-alone",
        "under-a-feature-never-started",
        "under-a-feature-completed-already",
        "the-last-work-item-of-its-feature",
        "a-task",
    ],
)
def test_a_completion_that_starts_no_work_item_says_what_the_completion_says(
    items: list[WorkItemState], feature: FeatureState, item: str, said: str
) -> None:
    written, _ = complete(items, feature, item=item)
    assert (written.out, written.branch) == (said, None)
