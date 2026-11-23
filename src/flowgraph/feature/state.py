"""The states of a Feature: in Backlog, started, then completed, blocked between, or removed.

A Feature is to its work items what a work item is to its Tasks: its state is its own, each a
type that carries what it needs and nothing else, and a move returns the Feature in its next
state (`flowgraph.feature.moves`). Removed stands apart from the flow.
"""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Evidence, evidence_text, said
from flowgraph.knowledge import KnowledgeLine
from flowgraph.parent import FeatureId, feature_id_text
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
    knowledge: tuple[KnowledgeLine, ...] = ()
    about: tuple[str, ...] = ()


@dataclass(frozen=True)
class StartedFeature:
    """A Feature in InProgress: started, its work items started side by side."""

    id: FeatureId
    title: str
    description: str
    criteria: tuple[str, ...]
    created: datetime
    started: datetime
    knowledge: tuple[KnowledgeLine, ...] = ()
    about: tuple[str, ...] = ()


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
    knowledge: tuple[KnowledgeLine, ...] = ()
    about: tuple[str, ...] = ()


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
    knowledge: tuple[KnowledgeLine, ...] = ()
    about: tuple[str, ...] = ()


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
    knowledge: tuple[KnowledgeLine, ...] = ()
    about: tuple[str, ...] = ()


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
    feature_id: FeatureId,
    title: str,
    criteria: Iterable[str],
    description: str,
    created: datetime,
    about: tuple[str, ...] = (),
) -> Feature:
    """A Feature with its criteria, its created time kept to the second, about those terms.

    Raises EmptyPartError when the title or a criterion is blank and NoCriterionError when it
    states none.
    """
    stated = tuple(said("criterion", criterion) for criterion in criteria)
    if not stated:
        raise NoCriterionError("a Feature states at least one criterion")
    to_the_second = created.replace(microsecond=0)
    titled = said("title", title)
    return Feature(feature_id, titled, description, stated, to_the_second, (), about)


def noted_feature[F: FeatureState](feature: F, line: KnowledgeLine) -> F:
    """The Feature, in whatever state, with the line after the lines it already keeps."""
    return replace(feature, knowledge=(*feature.knowledge, line))


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
