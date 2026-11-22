"""The start of a Feature with its first work item, and of a work item under a Feature."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import NO_COMMIT, make_scenario
from flowgraph.development import make_slug
from flowgraph.development.parallel import ParallelError
from flowgraph.feature import (
    FeatureNotFoundError,
    FeatureState,
    completed_feature,
    make_feature,
    started_feature,
)
from flowgraph.feature.start import (
    FeatureNotStartedError,
    NoWorkItemError,
    WorkItemInProgressError,
    check_start_under_feature,
    start_feature_item,
)
from flowgraph.item.commands import ToBranch, Written
from flowgraph.parent import STANDALONE, FeatureId, Parent, make_feature_id
from flowgraph.record import Config, make_config
from flowgraph.record.queue import Queue, make_queue
from flowgraph.record.store import FeatureStore, Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import (
    CompletedAlreadyError,
    NoTaskError,
    StartedAlreadyError,
    make_task,
    make_task_id,
)
from flowgraph.work_item import (
    WorkItem,
    WorkItemState,
    append_task,
    completed_task,
    completed_work_item,
    make_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

DAY = {number: datetime(2026, 1, number, tzinfo=UTC) for number in range(1, 9)}
NOW = datetime(2026, 2, 1, 9, 0, 0, tzinfo=UTC)
F1 = make_feature_id(1)
S1, S2, S3 = (make_story_id(number) for number in range(1, 4))
FEATURE = make_feature(F1, "a feature title", ["a criterion"], "", DAY[1])
STARTED = started_feature(FEATURE, DAY[5])
COMPLETED = completed_feature(STARTED, DAY[6], NO_COMMIT)
NO_QUEUE = make_queue([])
UNLIMITED = make_config("")
ONE_AT_ONCE = make_config("[development]\nenabled = true\nparallel = 1\n")


def never(*_: object) -> Never:
    """A read or a write of the record that the start of a Feature never asks for."""
    raise AssertionError("a start reads the rows, the queue, the Feature and its work item")


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
    """The Story of that number, started on the day after it was added."""
    return started_work_item(story(number, parent), DAY[number + 1])


def completed(number: int, parent: Parent = F1) -> WorkItemState:
    """The Story of that number, completed with its one Task on the day after it was added."""
    on = DAY[number + 1]
    begun = started_task(started(number, parent), make_task_id(number), on)
    done = completed_task(begun, make_task_id(number), on, NO_COMMIT)
    return completed_work_item(done, on, NO_COMMIT)


@dataclass
class Saved:
    """What a start saved: the Features and the work items, in the order saved."""

    features: list[FeatureState] = field(default_factory=list[FeatureState])
    items: list[WorkItemState] = field(default_factory=list[WorkItemState])


def store(
    items: Sequence[WorkItemState],
    feature: FeatureState = FEATURE,
    queue: Queue = NO_QUEUE,
    saved: Saved | None = None,
) -> Store:
    """The store of a record holding those Stories, that Feature and that queue."""
    kept = Saved() if saved is None else saved
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
        save_work_item=kept.items.append,
        load_queue=lambda: queue,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(load_feature, kept.features.append, lambda: ["F-0001"]),
    )


def start(
    items: Sequence[WorkItemState],
    feature: FeatureState = FEATURE,
    queue: Queue = NO_QUEUE,
    *,
    slug: str | None = None,
    config: Config = UNLIMITED,
    named: str = "F-0001",
) -> tuple[Written, Saved]:
    """Start the Feature named on a record of those Stories; what it says and what it saved."""
    saved = Saved()
    written = start_feature_item(
        named, slug, store(items, feature, queue, saved), lambda: NOW, config
    )
    return written, saved


def test_a_feature_started_says_its_first_work_item_and_names_the_branch_of_that_one() -> None:
    written, _ = start([story(1), story(2)])
    assert written == Written(
        "started F-0001 with S-0001\n",
        "chore: start F-0001 in the record",
        ToBranch(S1, make_slug("title-1")),
    )


def test_a_feature_started_is_saved_started_now() -> None:
    _, saved = start([story(1), story(2)])
    assert saved.features == [started_feature(FEATURE, NOW)]


def test_the_first_work_item_of_a_feature_started_is_saved_started_now_and_no_other() -> None:
    _, saved = start([story(1), story(2)])
    assert saved.items == [started_work_item(story(1), NOW)]


def test_the_first_work_item_is_the_first_in_backlog_in_the_order_of_the_queue() -> None:
    written, _ = start([story(1), story(2), story(3)], queue=make_queue([S3, S1, S2]))
    assert written.out == "started F-0001 with S-0003\n"


def test_a_feature_that_holds_completed_work_items_starts_with_the_next_in_backlog() -> None:
    written, _ = start([completed(1), story(2), story(3)])
    assert written.out == "started F-0001 with S-0002\n"


def test_a_work_item_standing_alone_is_not_the_first_of_a_feature() -> None:
    written, _ = start([story(1, STANDALONE), story(2)])
    assert written.out == "started F-0001 with S-0002\n"


def test_a_slug_given_names_the_branch_of_the_first_work_item() -> None:
    written, _ = start([story(1)], slug="a-slug")
    assert written.branch == ToBranch(S1, make_slug("a-slug"))


def test_a_feature_started_beside_fewer_started_than_parallel_starts() -> None:
    written, _ = start([story(1), completed(2, STANDALONE)], config=ONE_AT_ONCE)
    assert written.out == "started F-0001 with S-0001\n"


REFUSED = [
    ([], FEATURE, UNLIMITED, NoWorkItemError, "F-0001 has no work item in Backlog to start with"),
    (
        [completed(1), story(2, STANDALONE)],
        FEATURE,
        UNLIMITED,
        NoWorkItemError,
        "F-0001 has no work item in Backlog to start with",
    ),
    (
        [story(1, tasks=0), story(2)],
        FEATURE,
        UNLIMITED,
        NoTaskError,
        "F-0001 cannot start: S-0001 has no Task to start with",
    ),
    ([story(1)], STARTED, UNLIMITED, StartedAlreadyError, "F-0001 is started already"),
    ([story(1)], COMPLETED, UNLIMITED, CompletedAlreadyError, "F-0001 is completed already"),
    (
        [story(1), started(2, STANDALONE)],
        FEATURE,
        ONE_AT_ONCE,
        ParallelError,
        r"F-0001 cannot start: development\.parallel = 1, started already: S-0002",
    ),
]
REFUSALS = [
    "no-work-item",
    "no-work-item-in-backlog",
    "first-work-item-without-a-task",
    "started-already",
    "completed-already",
    "beside-as-many-started-as-parallel",
]


@pytest.mark.parametrize(("items", "feature", "config", "error", "message"), REFUSED, ids=REFUSALS)
def test_a_feature_start_refused_names_why(
    items: list[WorkItemState],
    feature: FeatureState,
    config: Config,
    error: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error, match=rf"^{message}$"):
        start(items, feature, config=config)


@pytest.mark.parametrize(("items", "feature", "config", "error", "message"), REFUSED, ids=REFUSALS)
def test_a_feature_start_refused_saves_nothing(
    items: list[WorkItemState],
    feature: FeatureState,
    config: Config,
    error: type[Exception],
    message: str,
) -> None:
    saved = Saved()
    with pytest.raises(error):
        start_feature_item("F-0001", None, store(items, feature, saved=saved), lambda: NOW, config)
    assert (saved.features, saved.items) == ([], [])


def test_a_feature_the_record_does_not_hold_is_not_started() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0009 in the record$"):
        start([story(1)], named="F-0009")


def test_a_work_item_started_before_its_feature_is_refused_naming_the_feature() -> None:
    with pytest.raises(
        FeatureNotStartedError,
        match=r"^S-0001 cannot start: F-0001 is not started, start it first$",
    ):
        check_start_under_feature("S-0001", store([story(1), story(2)]))


def test_a_work_item_started_beside_a_started_one_of_its_feature_is_refused_naming_that_one() -> (
    None
):
    with pytest.raises(
        WorkItemInProgressError,
        match=r"^S-0002 cannot start: F-0001 starts one work item at a time,"
        r" started already: S-0001$",
    ):
        check_start_under_feature("S-0002", store([started(1), story(2)], STARTED))


def test_a_work_item_started_under_a_completed_feature_is_refused_naming_the_feature() -> None:
    with pytest.raises(
        CompletedAlreadyError, match=r"^S-0002 cannot start: F-0001 is completed already$"
    ):
        check_start_under_feature("S-0002", store([completed(1), story(2)], COMPLETED))


def test_a_work_item_of_a_started_feature_with_none_started_passes() -> None:
    assert check_start_under_feature("S-0002", store([completed(1), story(2)], STARTED)) is None


def test_a_work_item_started_beside_a_started_one_standing_alone_passes() -> None:
    items = [started(1, STANDALONE), story(2)]
    assert check_start_under_feature("S-0002", store(items, STARTED)) is None


def test_a_work_item_standing_alone_passes() -> None:
    assert check_start_under_feature("S-0001", store([story(1, STANDALONE)])) is None


@pytest.mark.parametrize(
    ("item", "items"),
    [("S-0001", [started(1)]), ("S-0001", [completed(1)])],
    ids=["started", "completed"],
)
def test_a_work_item_not_in_backlog_under_a_feature_never_started_passes_to_the_start(
    item: str, items: list[WorkItemState]
) -> None:
    assert check_start_under_feature(item, store(items)) is None


@pytest.mark.parametrize("item", ["T-0001", "F-0001", "no-id"], ids=["task", "feature", "no-id"])
def test_what_is_no_work_item_passes_without_a_read_of_the_record(item: str) -> None:
    unread = Store(
        find_work_item_rows=never,
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )
    assert check_start_under_feature(item, unread) is None
