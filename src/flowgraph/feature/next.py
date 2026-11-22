"""The next work item of a started Feature: the completion of the one before starts it.

A Feature is to its work items what a work item is to its Tasks: it starts them one by one. The
completion of a work item under a started Feature starts the first of its work items in Backlog
in the order of the queue, in the same write, as `fgraph start` of that work item would. A next
work item that cannot start leaves the completion as it is, and the completion says why: a
blocked Feature starts none. It runs on the store of a record, as the commands of a work item
do (`flowgraph.item.commands`).
"""

from typing import assert_never

from flowgraph.development import SlugError
from flowgraph.development.parallel import ParallelError, check_parallel
from flowgraph.development.scope import OutOfScopeError
from flowgraph.feature import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    RemovedFeature,
    StartedFeature,
)
from flowgraph.feature.start import (
    WorkItemInProgressError,
    check_start_under_feature,
    first_in_backlog,
)
from flowgraph.item.commands import MESSAGE, Written, complete_item, parse_item_id, start_item
from flowgraph.parent import FeatureId, Standalone
from flowgraph.record import Config, Now
from flowgraph.record.store import Store
from flowgraph.relation.depends import StartWaitsError, check_start_waits
from flowgraph.task import BlockedError, NoTaskError, TaskId
from flowgraph.work_item import WorkItemId, work_item_id_text

# What leaves the next work item in Backlog: each refusal of its start, the completion standing.
NOT_STARTED = (
    NoTaskError,
    ParallelError,
    WorkItemInProgressError,
    BlockedError,
    StartWaitsError,
    OutOfScopeError,
    SlugError,
)


def _next_of(item_id: WorkItemId, store: Store) -> WorkItemId | None:
    """The work item the completion of that one starts; None when it starts none.

    It is the first work item in Backlog of the started Feature the work item is under: of a
    blocked one too, whose block then refuses its start. A work item standing alone starts
    none, and neither does one under a Feature never started, removed, or completed, with that
    completion or before it.
    """
    match store.load_work_item(item_id).parent:
        case Standalone():
            return None
        case FeatureId() as feature_id:
            feature = store.features.load_feature(feature_id)
        case _ as unreachable:
            assert_never(unreachable)
    match feature:
        case Feature() | CompletedFeature() | RemovedFeature():
            return None
        case StartedFeature() | BlockedFeature():
            return first_in_backlog(feature_id, store)
        case _ as unreachable:
            assert_never(unreachable)


def start_next(item_id: WorkItemId, store: Store, now: Now, config: Config) -> Written:
    """Start the work item in Backlog of that id, as `fgraph start` of it does; what it says.

    Raises one of NOT_STARTED when its Feature holds a started work item or is blocked, when it
    depends on a work item not completed, when as
    many are started as the configuration starts at once, when it has no Task, when its title
    gives no slug or when the branch written on writes another work item alone; nothing is
    saved.
    """
    named = work_item_id_text(item_id)
    check_start_under_feature(named, store)
    check_start_waits(named, store)
    check_parallel(named, store.find_work_item_rows, config)
    return start_item(named, None, store, now)


def complete_and_start_next(
    item: str, sha: str | None, store: Store, now: Now, config: Config, decision: str | None = None
) -> Written:
    """Complete the item of that id, and start the next work item of its Feature with it.

    The completion is that of `complete_item`, with its refusals. Under a started Feature it
    starts the next work item, named on a line of its own after the completion and in the
    message beside it, with the branch to check out at the commit of the write. A next work item
    that cannot start is named on that line with why, and the completion stands as written. A
    Task starts none, and neither does the last work item of a Feature, which completes it.
    """
    completed = complete_item(item, sha, store, now, config, decision)
    match parse_item_id(item):
        case TaskId():
            return completed
        case WorkItemId() as item_id:
            following = _next_of(item_id, store)
        case _ as unreachable:
            assert_never(unreachable)
    if following is None:
        return completed
    try:
        started = start_next(following, store, now, config)
    except NOT_STARTED as error:
        return Written(f"{completed.out}not started: {error}\n", completed.message)
    both = f"complete {work_item_id_text(item_id)} and start {work_item_id_text(following)}"
    return Written(completed.out + started.out, MESSAGE.format(both), started.branch)
