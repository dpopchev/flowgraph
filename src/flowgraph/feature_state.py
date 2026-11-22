"""The states of a Feature and the moves between them: in Backlog, started, then completed.

A Feature is to its work items what a work item is to its Tasks: its state is its own, each a
type that carries what it needs and nothing else, and a move returns the Feature in its next
state.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Evidence, evidence_text, said
from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.task import CompletedAlreadyError, NotStartedError, StartedAlreadyError

# The states of a Feature as the record writes them; a file without the line reads as in Backlog.
IN_BACKLOG = "backlog"
STARTED = "started"
COMPLETED = "completed"


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


# A Feature in any of its states, as the record keeps it.
FeatureState = Feature | StartedFeature | CompletedFeature


class NoCriterionError(ValueError):
    """A Feature without a criterion."""


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

    Raises StartedAlreadyError when it is started and CompletedAlreadyError when it is
    completed.
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
        case CompletedFeature():
            raise CompletedAlreadyError(f"{feature_id_text(feature.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def completed_feature(feature: FeatureState, on: datetime, commit: Evidence) -> CompletedFeature:
    """The started Feature completed on that time, kept to the second, in that commit or none.

    Raises NotStartedError when it is in Backlog and CompletedAlreadyError when it is completed.
    """
    match feature:
        case Feature():
            raise NotStartedError(f"{feature_id_text(feature.id)} is in Backlog: start it first")
        case StartedFeature():
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
        case _ as unreachable:
            assert_never(unreachable)


def commit_sha(feature: FeatureState) -> str:
    """The sha of the commit of a completed Feature; empty for one that has none."""
    match feature:
        case CompletedFeature():
            return evidence_text(feature.commit)
        case Feature() | StartedFeature():
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
        case CompletedFeature():
            return COMPLETED
        case _ as unreachable:
            assert_never(unreachable)
