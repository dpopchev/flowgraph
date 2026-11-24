"""The removal of a Feature, beside that of a work item and of a Task: `fgraph remove` takes all.

A Feature is to its work items what a work item is to its Tasks: one in Backlog, started or
blocked is removed with its reason, and its work items in Backlog are removed with it, for the
same reason, as a removed work item keeps its Tasks; a completed one stays. A Task of a started
work item is removed alone, from its work item. Nothing is deleted. It runs on the store of a
record, as the commands of a work item do (`flowgraph.item.commands`).
"""

from datetime import datetime
from typing import assert_never

from flowgraph.feature import Feature, removed_feature
from flowgraph.item.commands import MESSAGE, Written, remove_item
from flowgraph.item.id import parse_moved_id
from flowgraph.item.moves import load_holder
from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.record import Now
from flowgraph.record.store import Store
from flowgraph.relation import RelationError
from flowgraph.relation.depends import superseded_by_asked
from flowgraph.status import rows_by_id
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    StartedAlreadyError,
    TaskId,
    task_id_text,
)
from flowgraph.work_item import (
    BlockedWorkItem,
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemId,
    WorkItemState,
    remove_task,
    removed_work_item,
    work_item_id_text,
)


def _removed_with(
    feature: str, item: WorkItemState, reason: str, on: datetime, begun: bool
) -> RemovedWorkItem | None:
    """The work item of the Feature of that name removed with it; None for one left as it is.

    One removed before stays as it was, with the reason it had; under a Feature begun, started
    or blocked, a completed one stays too. Raises StartedAlreadyError, BlockedError or
    CompletedAlreadyError naming the Feature and the work item that is started, blocked, or
    completed under one in Backlog.
    """
    named = work_item_id_text(item.id)
    match item:
        case WorkItem():
            return removed_work_item(item, reason, on)
        case RemovedWorkItem():
            return None
        case StartedWorkItem():
            raise StartedAlreadyError(f"{feature} cannot be removed: {named} is started already")
        case BlockedWorkItem():
            raise BlockedError(f"{feature} cannot be removed: {named} is blocked")
        case CompletedWorkItem() if begun:
            return None
        case CompletedWorkItem():
            raise CompletedAlreadyError(
                f"{feature} cannot be removed: {named} is completed already"
            )
        case _ as unreachable:
            assert_never(unreachable)


def _remove_task(task_id: TaskId, reason: str, store: Store, now: Now) -> Written:
    """Remove the Task of that id from its started work item for the reason; what it says."""
    holder = remove_task(
        task_id=task_id,
        reason=reason,
        load_holder=load_holder(store),
        save_work_item=store.save_work_item,
        now=now,
    )
    moved = f"{task_id_text(task_id)} of {work_item_id_text(holder)}"
    return Written(f"removed {moved}\n", MESSAGE.format(f"remove {moved}"))


def remove_named(
    item: str, reason: str | None, store: Store, now: Now, superseded_by: str | None = None
) -> Written:
    """Remove the Feature, the work item in Backlog or the Task of that id for the reason given.

    Returns what the write says. A work item may name the one that supersedes it in place of the
    reason or beside it; a Feature and a Task take the reason alone. A Task of a started work
    item is removed from it, in Backlog, started or blocked. A Feature is removed with every work
    item of it in Backlog, each for the same reason, as one write; one removed before stays as
    it was, and under a started or blocked Feature a completed one does too. The Feature is
    saved first, so a save of it refused, as on the branch of a work item, leaves nothing
    written. Raises ItemIdError naming every kind when the text is the id of none, TaskIdError
    or FeatureIdError for an id below 1, FeatureNotFoundError when the record holds no such
    Feature, EmptyPartError when the reason is blank, CompletedAlreadyError or
    RemovedAlreadyError when the Feature is completed or removed, and StartedAlreadyError when a
    work item of it is started, or CompletedAlreadyError when one is completed under a Feature
    in Backlog; for a Task the refusal of `remove_task`, for a work item that of `remove_item`
    or of `superseded_by_asked`. RelationError when neither is given and when a Feature or a
    Task is given what supersedes it. Nothing is saved.
    """
    if reason is None and superseded_by is None:
        raise RelationError("a remove takes --reason or --superseded-by, or both")
    match parse_moved_id(item):
        case WorkItemId():
            superseding = superseded_by_asked(superseded_by, item, store)
            return remove_item(item, reason or "", store, now, superseding)
        case TaskId() as task_id if superseded_by is not None:
            named = task_id_text(task_id)
            raise RelationError(f"{named} is a Task: it is removed with --reason alone")
        case TaskId() as task_id:
            return _remove_task(task_id, reason or "", store, now)
        case FeatureId() if superseded_by is not None:
            raise RelationError(f"{item} is a Feature: it is removed with --reason alone")
        case FeatureId() as feature_id:
            return _remove_feature(feature_id, reason or "", store, now)
        case _ as unreachable:
            assert_never(unreachable)


def _remove_feature(feature_id: FeatureId, reason: str, store: Store, now: Now) -> Written:
    """Remove the Feature of that id with its work items in Backlog for the reason; what it says."""
    named = feature_id_text(feature_id)
    on = now()
    loaded = store.features.load_feature(feature_id)
    removed = removed_feature(loaded, reason, on)
    begun = not isinstance(loaded, Feature)
    under = [item_id for item_id, row in rows_by_id(store).items() if row.parent == named]
    with_it = [
        _removed_with(named, store.load_work_item(held), reason, on, begun) for held in under
    ]
    store.features.save_feature(removed)
    for gone in with_it:
        if gone is not None:
            store.save_work_item(gone)
    return Written(f"removed {named}\n", MESSAGE.format(f"remove {named}"))
