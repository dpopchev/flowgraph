"""The views of a Feature: its detail, its row in a list and the bucket a list shows it in.

Every bucket but those its own state gives is derived from the states of its work items, as the
record writes them.
"""

from collections.abc import Collection
from dataclasses import dataclass, field
from typing import assert_never

from flowgraph.feature.state import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureState,
    RemovedFeature,
    StartedFeature,
    block_of,
    commit_sha,
    removal_reason,
)
from flowgraph.knowledge import KnowledgeRow, knowledge_row
from flowgraph.parent import feature_id_text
from flowgraph.work_item import WorkItemRow

# The states of a completed and of a removed work item, as the record writes them.
COMPLETED = "completed"
REMOVED = "removed"

# The states of a work item that leave nothing more to do on it.
DONE = frozenset({COMPLETED, REMOVED})

# The states of a work item that say work on it has begun.
BEGUN = frozenset({"started", COMPLETED})


@dataclass
class FeatureDetail:
    """One Feature as plain data, as a view reads it from the record; a commit once it has one.

    Its reason and what it waits on while it is blocked; its reason alone once it is removed;
    both empty otherwise.
    """

    id: str
    title: str
    description: str
    criteria: list[str]
    commit: str = ""
    reason: str = ""
    waiting_on: str = ""
    knowledge: list[KnowledgeRow] = field(default_factory=list[KnowledgeRow])
    about: list[str] = field(default_factory=list[str])


@dataclass
class FeatureRow:
    """One Feature as a line of a list reads it: its id, its title and its bucket.

    Its progress is the work items completed of those it holds; a removed one is not held. Its
    started work items are the rows a list writes under it, in the order given. Its commit is
    the one it was completed in, empty while it has none; what it waits on while it is blocked;
    its reason the one it was removed for, empty unless it is removed; its block reason the one
    it was blocked for, empty unless it is blocked.
    """

    id: str
    title: str
    bucket: str
    completed: int
    held: int
    started: list[WorkItemRow] = field(default_factory=list[WorkItemRow], kw_only=True)
    commit: str = field(default="", kw_only=True)
    waiting_on: str = field(default="", kw_only=True)
    reason: str = field(default="", kw_only=True)
    block_reason: str = field(default="", kw_only=True)


def feature_detail(feature: FeatureState) -> FeatureDetail:
    """The Feature as the plain data a view reads."""
    reason, waiting_on = block_of(feature)
    return FeatureDetail(
        feature_id_text(feature.id),
        feature.title,
        feature.description,
        list(feature.criteria),
        commit_sha(feature),
        reason or removal_reason(feature),
        waiting_on,
        [knowledge_row(line) for line in feature.knowledge],
        list(feature.about),
    )


def bucket_of(states: Collection[str]) -> str:
    """The bucket of a Feature, derived from the states of its work items as the record writes them.

    Completed when each is completed or removed; InProgress once one is started or completed
    while another is not; Backlog otherwise, as with no work item.
    """
    if states and all(state in DONE for state in states):
        return "Completed"
    if any(state in BEGUN for state in states):
        return "InProgress"
    return "Backlog"


def feature_bucket(feature: FeatureState, states: Collection[str]) -> str:
    """The bucket a list shows the Feature in, given the states of its work items.

    A started Feature is in InProgress, blocked or not, a completed one in Completed and a
    removed one in Removed, each by its own state: only the completion of its last work item
    completes a started Feature, so one whose work items are all completed or removed stays in
    InProgress. Every bucket of a Feature never started stays derived, as that of one whose work
    items were started before a Feature had a state.
    """
    match feature:
        case Feature():
            return bucket_of(states)
        case StartedFeature() | BlockedFeature():
            return "InProgress"
        case CompletedFeature():
            return "Completed"
        case RemovedFeature():
            return "Removed"
        case _ as unreachable:
            assert_never(unreachable)


def feature_row(feature: FeatureState, states: Collection[str]) -> FeatureRow:
    """The Feature as the row a list reads, in its bucket over the states of its work items.

    Its work items completed and held are counted from the same states, as the record writes them.
    """
    completed = sum(state == COMPLETED for state in states)
    held = sum(state != REMOVED for state in states)
    return FeatureRow(
        feature_id_text(feature.id),
        feature.title,
        feature_bucket(feature, states),
        completed,
        held,
        commit=commit_sha(feature),
        waiting_on=block_of(feature)[1],
        reason=removal_reason(feature),
        block_reason=block_of(feature)[0],
    )
