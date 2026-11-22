"""The states of a Feature and the moves between them: in Backlog, started, then completed.

A Feature is to its work items what a work item is to its Tasks: its state is its own, each a
type that carries what it needs and nothing else, and a move returns the Feature in its next
state. A started one is blocked and unblocked back to started, as a Task is. One in Backlog is
removed with its reason: Removed stands apart from the flow, and a removed Feature takes no move.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Evidence, evidence_text, said
from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    NotBlockedError,
    NotStartedError,
    StartedAlreadyError,
)
from flowgraph.work_item import RemovedAlreadyError

# The states of a Feature as the record writes them; a file without the line reads as in Backlog.
IN_BACKLOG = "backlog"
STARTED = "started"
BLOCKED = "blocked"
COMPLETED = "completed"
REMOVED = "removed"


@dataclass(frozen=True)
class Feature:
    """A Feature in Backlog: its outcome title, its description and its criteria, one or more."""

    id: FeatureId
    title: str
    description: str
    criteria: tuple[str, ...]
    created: datetime


@dataclass(frozen=True)
class StartedFeature:
    """A Feature in InProgress: started, its work items started one at a time."""

    id: FeatureId
    title: str
    description: str
    criteria: tuple[str, ...]
    created: datetime
    started: datetime


@dataclass(frozen=True)
class BlockedFeature:
    """A Feature in InProgress that cannot go on: its reason, since when, and what it waits on."""

    id: FeatureId
    title: str
    description: str
    criteria: tuple[str, ...]
    created: datetime
    started: datetime
    reason: str
    since: datetime
    waiting_on: str


@dataclass(frozen=True)
class CompletedFeature:
    """A Feature in Completed: completed with its last work item, in the commit of that one."""

    id: FeatureId
    title: str
    description: str
    criteria: tuple[str, ...]
    created: datetime
    started: datetime
    completed: datetime
    commit: Evidence


@dataclass(frozen=True)
class RemovedFeature:
    """A Feature in Removed: out of the flow from Backlog, kept whole with when and why."""

    id: FeatureId
    title: str
    description: str
    criteria: tuple[str, ...]
    created: datetime
    removed: datetime
    reason: str


# A Feature in any of its states, as the record keeps it.
FeatureState = Feature | StartedFeature | BlockedFeature | CompletedFeature | RemovedFeature


class NoCriterionError(ValueError):
    """A Feature without a criterion."""


class FeatureRemovedError(RemovedAlreadyError):
    """A removed Feature moved, amended or given a work item; the message names it.

    It is the refusal of a removed work item, so what refuses the one refuses the other.
    `refused` says what is refused, up to the Feature: `S-0001 cannot start: `.
    """

    def __init__(self, feature_id: FeatureId, refused: str = "") -> None:
        ValueError.__init__(self, f"{refused}{feature_id_text(feature_id)} is removed already")


def make_feature(
    feature_id: FeatureId, title: str, criteria: Iterable[str], description: str, created: datetime
) -> Feature:
    """A Feature with its criteria, its created time kept to the second.

    Raises EmptyPartError when the title or a criterion is blank and NoCriterionError when it
    states none.
    """
    stated = tuple(said("criterion", criterion) for criterion in criteria)
    if not stated:
        raise NoCriterionError("a Feature states at least one criterion")
    to_the_second = created.replace(microsecond=0)
    return Feature(feature_id, said("title", title), description, stated, to_the_second)


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
            )
        case CompletedFeature():
            raise CompletedAlreadyError(f"{feature_id_text(feature.id)} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature.id)
        case _ as unreachable:
            assert_never(unreachable)


def removed_feature(feature: FeatureState, reason: str, on: datetime) -> RemovedFeature:
    """The Feature in Backlog removed on that time, kept to the second, for the reason given.

    Raises EmptyPartError when the reason is blank, StartedAlreadyError when the Feature is
    started, BlockedError when it is blocked, CompletedAlreadyError when it is completed and
    RemovedAlreadyError when it is removed.
    """
    match feature:
        case Feature():
            return RemovedFeature(
                feature.id,
                feature.title,
                feature.description,
                feature.criteria,
                feature.created,
                on.replace(microsecond=0),
                said("reason", reason),
            )
        case StartedFeature():
            raise StartedAlreadyError(f"{feature_id_text(feature.id)} is started already")
        case BlockedFeature():
            raise BlockedError(f"{feature_id_text(feature.id)} is blocked")
        case CompletedFeature():
            raise CompletedAlreadyError(f"{feature_id_text(feature.id)} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature.id)
        case _ as unreachable:
            assert_never(unreachable)


def commit_sha(feature: FeatureState) -> str:
    """The sha of the commit of a completed Feature; empty for one that has none."""
    match feature:
        case CompletedFeature():
            return evidence_text(feature.commit)
        case Feature() | StartedFeature() | BlockedFeature() | RemovedFeature():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def block_of(feature: FeatureState) -> tuple[str, str]:
    """The reason of a blocked Feature and what it waits on; both empty for one not blocked."""
    match feature:
        case BlockedFeature():
            return feature.reason, feature.waiting_on
        case Feature() | StartedFeature() | CompletedFeature() | RemovedFeature():
            return "", ""
        case _ as unreachable:
            assert_never(unreachable)


def removal_reason(feature: FeatureState) -> str:
    """The reason a removed Feature was removed for; empty for one that is not removed."""
    match feature:
        case RemovedFeature():
            return feature.reason
        case Feature() | StartedFeature() | BlockedFeature() | CompletedFeature():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def state_name(feature: FeatureState) -> str:
    """The state of a Feature as the record writes it."""
    match feature:
        case Feature():
            return IN_BACKLOG
        case StartedFeature():
            return STARTED
        case BlockedFeature():
            return BLOCKED
        case CompletedFeature():
            return COMPLETED
        case RemovedFeature():
            return REMOVED
        case _ as unreachable:
            assert_never(unreachable)
