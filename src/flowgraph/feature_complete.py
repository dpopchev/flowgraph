"""The completion of a Feature: it completes with its last work item, in the same write.

A Feature is to its work items what a work item is to its Tasks: a started Feature is completed
by the completion that leaves each work item of it completed or removed, at the time and in the
commit of that completion. Only a completion completes it: the removal of its last work item in
Backlog leaves it started. It runs on the store of a record, as the commands of a work item do
(`flowgraph.item`).
"""

from typing import assert_never

from flowgraph import work_item
from flowgraph.criterion import Evidence
from flowgraph.feature import (
    DONE,
    BlockedFeature,
    CompletedFeature,
    Feature,
    StartedFeature,
    completed_feature,
)
from flowgraph.parent import FeatureId, Standalone, feature_id_text
from flowgraph.record import Now
from flowgraph.status import rows_by_id
from flowgraph.store import Store
from flowgraph.work_item import CompletedWorkItem, WorkItemId


def completed_with(done: CompletedWorkItem, store: Store) -> CompletedFeature | None:
    """The Feature the completion of the work item completes, completed; None when it does none.

    It is the started Feature the work item is under, blocked or not, once each other work item
    of it is completed or removed, at the completed time and in the commit of the work item. A
    work item standing alone completes none, and neither does one under a Feature never
    started, whose bucket stays derived, or under one completed already. Raises
    FeatureNotFoundError when the record holds no Feature of the id the work item names.
    """
    match done.parent:
        case Standalone():
            return None
        case FeatureId() as feature_id:
            feature = store.features.load_feature(feature_id)
        case _ as unreachable:
            assert_never(unreachable)
    match feature:
        case Feature() | CompletedFeature():
            return None
        case StartedFeature() | BlockedFeature():
            named = feature_id_text(feature_id)
            others = [
                row
                for item_id, row in rows_by_id(store).items()
                if row.parent == named and item_id != done.id
            ]
            if all(row.state in DONE for row in others):
                return completed_feature(feature, done.completed, done.commit)
            return None
        case _ as unreachable:
            assert_never(unreachable)


def complete_with_feature(
    item_id: WorkItemId, commit: Evidence, decision: str | None, store: Store, now: Now
) -> FeatureId | None:
    """Complete the work item of that id now, and its Feature with it when it is the last.

    Returns the Feature completed, None when the completion completes none. The Feature is
    saved first, so a save of it refused, as on the branch of the work item, which writes that
    work item alone, leaves nothing written. Raises the refusal of the completion of the work
    item, as `work_item.complete_work_item` does; nothing is saved.
    """
    done = work_item.completed_work_item(store.load_work_item(item_id), now(), commit, decision)
    feature = completed_with(done, store)
    if feature is not None:
        store.features.save_feature(feature)
    store.save_work_item(done)
    return None if feature is None else feature.id
