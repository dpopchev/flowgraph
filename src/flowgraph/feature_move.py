"""The move of a work item between Features: what a Feature asks of one put under it or taken out.

A work item in Backlog is put under a Feature, or taken out of one, by its amend
(`flowgraph.work_item.amend`). It is put under a Feature in Backlog, started or blocked, by the
one rule an add follows too (B-0016), never under a completed or a removed one. The Feature it
is taken out of is in Backlog, as the work item is: a started one starts its work items one by
one, so what it holds is not taken from it.
"""

from typing import assert_never

from flowgraph.feature import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureRemovedError,
    LoadFeature,
    RemovedFeature,
    StartedFeature,
)
from flowgraph.parent import FeatureId, Parent, Standalone, feature_id_text
from flowgraph.task import BlockedError, CompletedAlreadyError, StartedAlreadyError
from flowgraph.work_item import WorkItemId, work_item_id_text


def _check_in_backlog(moved: str, parent: Parent, load_feature: LoadFeature) -> None:
    """Check that the parent is a Feature in Backlog, or standing alone, which asks nothing.

    `moved` says the move refused, up to the Feature: `S-0001 cannot be put under`.
    """
    match parent:
        case Standalone():
            return
        case FeatureId():
            named = feature_id_text(parent)
        case _ as unreachable:
            assert_never(unreachable)
    match load_feature(parent):
        case Feature():
            return
        case StartedFeature():
            raise StartedAlreadyError(f"{moved} {named}: {named} is started already")
        case BlockedFeature():
            raise BlockedError(f"{moved} {named}: {named} is blocked")
        case CompletedFeature():
            raise CompletedAlreadyError(f"{moved} {named}: {named} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(parent, f"{moved} {named}: ")
        case _ as unreachable:
            assert_never(unreachable)


def _check_takes(moved: str, parent: Parent, load_feature: LoadFeature) -> None:
    """Check that the parent is a Feature that takes a work item, or standing alone.

    A Feature in Backlog, started or blocked takes one; `moved` says the move refused, up to
    the Feature: `S-0001 cannot be put under`.
    """
    match parent:
        case Standalone():
            return
        case FeatureId():
            named = feature_id_text(parent)
        case _ as unreachable:
            assert_never(unreachable)
    match load_feature(parent):
        case Feature() | StartedFeature() | BlockedFeature():
            return
        case CompletedFeature():
            raise CompletedAlreadyError(f"{moved} {named}: {named} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(parent, f"{moved} {named}: ")
        case _ as unreachable:
            assert_never(unreachable)


def check_move(load_feature: LoadFeature, item_id: WorkItemId, was: Parent, now: Parent) -> None:
    """Check the Feature the work item is put under, and that the one it leaves is in Backlog.

    The one it is put under is read first: it is in Backlog, started or blocked, as for an add.
    Raises FeatureNotFoundError when the record holds no such Feature, CompletedAlreadyError or
    RemovedAlreadyError naming the work item and the Feature it is put under when that one is
    completed or removed, and StartedAlreadyError, BlockedError, CompletedAlreadyError or
    RemovedAlreadyError naming it and the Feature it leaves when that one is not in Backlog.
    """
    named = work_item_id_text(item_id)
    _check_takes(f"{named} cannot be put under", now, load_feature)
    _check_in_backlog(f"{named} cannot be taken out of", was, load_feature)
