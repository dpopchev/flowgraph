"""The removal of a Feature, beside that of a work item: `fgraph remove` takes both.

A Feature is to its work items what a work item is to its Tasks: one in Backlog is removed with
its reason, and its work items are removed with it, for the same reason, as a removed work item
keeps its Tasks. Nothing is deleted. It runs on the store of a record, as the commands of a work
item do (`flowgraph.item`).
"""

from datetime import datetime
from typing import assert_never

from flowgraph.feature import removed_feature
from flowgraph.feature_item import is_feature_id
from flowgraph.item import MESSAGE, Written, remove_item
from flowgraph.parent import feature_id_text, parse_feature_id
from flowgraph.record import Now
from flowgraph.status import rows_by_id
from flowgraph.store import Store
from flowgraph.task import CompletedAlreadyError, StartedAlreadyError
from flowgraph.work_item import (
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
    removed_work_item,
    work_item_id_text,
)


def _removed_with(
    feature: str, item: WorkItemState, reason: str, on: datetime
) -> RemovedWorkItem | None:
    """The work item of the Feature of that name removed with it; None for one removed before.

    One removed before stays as it was, with the reason it had. Raises StartedAlreadyError or
    CompletedAlreadyError naming the Feature and the work item that is started or completed.
    """
    named = work_item_id_text(item.id)
    match item:
        case WorkItem():
            return removed_work_item(item, reason, on)
        case RemovedWorkItem():
            return None
        case StartedWorkItem():
            raise StartedAlreadyError(f"{feature} cannot be removed: {named} is started already")
        case CompletedWorkItem():
            raise CompletedAlreadyError(
                f"{feature} cannot be removed: {named} is completed already"
            )
        case _ as unreachable:
            assert_never(unreachable)


def remove_named(item: str, reason: str, store: Store, now: Now) -> Written:
    """Remove the Feature or the work item in Backlog of that id for the reason given.

    Returns what the write says. A Feature is removed with every work item under it, each for
    the same reason, as one write; one of them removed before stays as it was. The Feature is
    saved first, so a save of it refused, as on the branch of a work item, leaves nothing
    written. Raises FeatureNotFoundError when the record holds no such Feature, EmptyPartError
    when the reason is blank, StartedAlreadyError, BlockedError, CompletedAlreadyError or
    RemovedAlreadyError when the Feature is not in Backlog, and StartedAlreadyError or
    CompletedAlreadyError when a work item of it is started or completed; for any other id the
    refusal of `remove_item`. Nothing is saved.
    """
    if not is_feature_id(item):
        return remove_item(item, reason, store, now)
    feature_id = parse_feature_id(item)
    named = feature_id_text(feature_id)
    on = now()
    removed = removed_feature(store.features.load_feature(feature_id), reason, on)
    under = [item_id for item_id, row in rows_by_id(store).items() if row.parent == named]
    with_it = [_removed_with(named, store.load_work_item(held), reason, on) for held in under]
    store.features.save_feature(removed)
    for gone in with_it:
        if gone is not None:
            store.save_work_item(gone)
    return Written(f"removed {named}\n", MESSAGE.format(f"remove {named}"))
