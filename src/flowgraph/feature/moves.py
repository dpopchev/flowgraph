"""The moves of a Feature between its states: each returns the Feature in its next state.

A started one is blocked and unblocked back to started, as a Task is; one in Backlog, started or
blocked is removed with its reason, and a removed Feature takes no move.
"""

from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Evidence, said
from flowgraph.feature.state import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureRemovedError,
    FeatureState,
    RemovedFeature,
    StartedFeature,
)
from flowgraph.parent import feature_id_text
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    NotBlockedError,
    NotStartedError,
    StartedAlreadyError,
)


def started_feature(feature: FeatureState, on: datetime) -> StartedFeature:
    """The Feature started on that time, kept to the second, holding what it held.

    Raises StartedAlreadyError when it is started, BlockedError when it is blocked,
    CompletedAlreadyError when it is completed and RemovedAlreadyError when it is removed.
    """
    match feature:
        case Feature():
            return StartedFeature(
                feature.id,
                feature.title,
                feature.description,
                feature.criteria,
                feature.created,
                on.replace(microsecond=0),
                feature.knowledge,
                feature.about,
            )
        case StartedFeature():
            raise StartedAlreadyError(f"{feature_id_text(feature.id)} is started already")
        case BlockedFeature():
            raise BlockedError(f"{feature_id_text(feature.id)} is blocked: unblock it first")
        case CompletedFeature():
            raise CompletedAlreadyError(f"{feature_id_text(feature.id)} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature.id)
        case _ as unreachable:
            assert_never(unreachable)


def blocked_feature(
    feature: FeatureState, reason: str, waiting_on: str, on: datetime
) -> BlockedFeature:
    """The started Feature blocked on that time, kept to the second, for the reason given.

    Raises NotStartedError when it is in Backlog, BlockedError when it is blocked already,
    CompletedAlreadyError when it is completed, RemovedAlreadyError when it is removed and
    EmptyPartError when the reason or what it waits on is blank.
    """
    match feature:
        case Feature():
            raise NotStartedError(f"{feature_id_text(feature.id)} is in Backlog: start it first")
        case StartedFeature():
            return BlockedFeature(
                feature.id,
                feature.title,
                feature.description,
                feature.criteria,
                feature.created,
                feature.started,
                said("reason", reason),
                on.replace(microsecond=0),
                said("waiting on", waiting_on),
                feature.knowledge,
                feature.about,
            )
        case BlockedFeature():
            raise BlockedError(f"{feature_id_text(feature.id)} is blocked already")
        case CompletedFeature():
            raise CompletedAlreadyError(f"{feature_id_text(feature.id)} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature.id)
        case _ as unreachable:
            assert_never(unreachable)


def unblocked_feature(feature: FeatureState) -> StartedFeature:
    """The blocked Feature started again, with the started time it had; its block is dropped.

    Raises NotBlockedError when it is in Backlog, started, completed or removed.
    """
    match feature:
        case BlockedFeature():
            return StartedFeature(
                feature.id,
                feature.title,
                feature.description,
                feature.criteria,
                feature.created,
                feature.started,
                feature.knowledge,
                feature.about,
            )
        case Feature() | StartedFeature() | CompletedFeature() | RemovedFeature():
            raise NotBlockedError(f"{feature_id_text(feature.id)} is not blocked")
        case _ as unreachable:
            assert_never(unreachable)


def completed_feature(feature: FeatureState, on: datetime, commit: Evidence) -> CompletedFeature:
    """The started Feature completed on that time, kept to the second, in that commit or none.

    A blocked one is completed as a started one is, its block dropped: its last work item
    completes it. Raises NotStartedError when it is in Backlog, CompletedAlreadyError when it
    is completed and RemovedAlreadyError when it is removed.
    """
    match feature:
        case Feature():
            raise NotStartedError(f"{feature_id_text(feature.id)} is in Backlog: start it first")
        case StartedFeature() | BlockedFeature():
            return CompletedFeature(
                feature.id,
                feature.title,
                feature.description,
                feature.criteria,
                feature.created,
                feature.started,
                on.replace(microsecond=0),
                commit,
                feature.knowledge,
                feature.about,
            )
        case CompletedFeature():
            raise CompletedAlreadyError(f"{feature_id_text(feature.id)} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature.id)
        case _ as unreachable:
            assert_never(unreachable)


def removed_feature(feature: FeatureState, reason: str, on: datetime) -> RemovedFeature:
    """The Feature removed on that time, kept to the second, for the reason given.

    One in Backlog, started or blocked is removed; a started time and a block are dropped.
    Raises EmptyPartError when the reason is blank, CompletedAlreadyError when it is completed
    and RemovedAlreadyError when it is removed.
    """
    match feature:
        case Feature() | StartedFeature() | BlockedFeature():
            return RemovedFeature(
                feature.id,
                feature.title,
                feature.description,
                feature.criteria,
                feature.created,
                on.replace(microsecond=0),
                said("reason", reason),
                feature.knowledge,
                feature.about,
            )
        case CompletedFeature():
            raise CompletedAlreadyError(f"{feature_id_text(feature.id)} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature.id)
        case _ as unreachable:
            assert_never(unreachable)
