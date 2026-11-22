"""A Feature: a bigger outcome that groups work items, with the criteria the user experiences.

It is not worked on directly, so it holds no Task. Its state is its own, in Backlog, started,
blocked, completed or removed, as that of a work item is (`flowgraph.feature_state`); a started
one is in InProgress, blocked or not, a completed one in Completed and a removed one in Removed,
and every other bucket a list shows it in is still derived from the states of its work items. It
is kept as one file of the record, `items/F-0001.toml` (`flowgraph.feature_file`).
"""

from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, field
from typing import assert_never

from flowgraph.feature_file import (
    FeatureFileError,
    FeatureMismatchError,
    FeatureNotFoundError,
    feature_file,
    read_feature,
    read_feature_ids,
    write_feature,
)
from flowgraph.feature_state import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureRemovedError,
    FeatureState,
    NoCriterionError,
    RemovedFeature,
    StartedFeature,
    block_of,
    blocked_feature,
    commit_sha,
    completed_feature,
    make_feature,
    noted_feature,
    removal_reason,
    removed_feature,
    started_feature,
    unblocked_feature,
)
from flowgraph.knowledge import KnowledgeKind, KnowledgeRow, knowledge_row, make_knowledge_line
from flowgraph.parent import FeatureId, feature_id_text, make_feature_id, parse_feature_id
from flowgraph.record import Now
from flowgraph.work_item import WorkItemRow

# The states of a Feature and its moves live in feature_state.py and its file in feature_file.py;
# they stay importable from here.
__all__ = [
    "BlockedFeature",
    "CompletedFeature",
    "Feature",
    "FeatureFileError",
    "FeatureMismatchError",
    "FeatureNotFoundError",
    "FeatureRemovedError",
    "FeatureState",
    "NoCriterionError",
    "RemovedFeature",
    "StartedFeature",
    "blocked_feature",
    "completed_feature",
    "feature_file",
    "make_feature",
    "note_feature",
    "noted_feature",
    "read_feature",
    "read_feature_ids",
    "removed_feature",
    "started_feature",
    "unblocked_feature",
    "write_feature",
]

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
    its reason the one it was removed for, empty unless it is removed.
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


# The Feature of that id, whole; raises FeatureNotFoundError when the record holds none.
LoadFeature = Callable[[FeatureId], FeatureState]

# Save the Feature whole.
SaveFeature = Callable[[FeatureState], None]

# The ids of the Features in the record, as written; an empty list when it holds none.
FindFeatureIds = Callable[[], list[str]]


def next_feature_id(taken: Collection[FeatureId]) -> FeatureId:
    """The next free Feature id: one above the highest taken, the first when none is."""
    return make_feature_id(max((feature_id.number for feature_id in taken), default=0) + 1)


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
    )


def note_feature(
    *,
    feature_id: FeatureId,
    kind: KnowledgeKind,
    text: str,
    load_feature: LoadFeature,
    save_feature: SaveFeature,
    now: Now,
    about: tuple[str, ...] = (),
) -> None:
    """Keep a line of that kind and text on the Feature of that id, in any state, and save it.

    The line is about the terms given and goes after the lines the Feature keeps. Raises
    FeatureNotFoundError when the record holds no such Feature and EmptyPartError when the text
    is blank; nothing is saved.
    """
    line = make_knowledge_line(kind, text, now(), about)
    save_feature(noted_feature(load_feature(feature_id), line))


def add_feature(
    *,
    title: str,
    criteria: Iterable[str],
    description: str,
    find_feature_ids: FindFeatureIds,
    save_feature: SaveFeature,
    now: Now,
    about: tuple[str, ...] = (),
) -> FeatureId:
    """Add a Feature under its next free id, about the terms given, and return that id.

    Raises EmptyPartError when the title or a criterion is blank and NoCriterionError when it
    states none; nothing is saved.
    """
    taken = [parse_feature_id(text) for text in find_feature_ids()]
    feature = make_feature(next_feature_id(taken), title, criteria, description, now(), about)
    save_feature(feature)
    return feature.id
