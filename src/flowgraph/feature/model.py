"""A Feature: a bigger outcome that groups work items, with the criteria the user experiences.

It is not worked on directly, so it holds no Task. Its state is its own, in Backlog, started,
blocked, completed or removed, as that of a work item is (`flowgraph.feature.state`); a started
one is in InProgress, blocked or not, a completed one in Completed and a removed one in Removed,
and every other bucket a list shows it in is still derived from the states of its work items. It
is kept as one file of the record, `items/F-0001.toml` (`flowgraph.feature.file`). Its detail,
its row and its bucket are its views (`flowgraph.feature.views`).
"""

from collections.abc import Callable, Collection, Iterable

from flowgraph.feature.file import (
    FeatureFileError,
    FeatureMismatchError,
    FeatureNotFoundError,
    feature_file,
    read_feature,
    read_feature_ids,
    write_feature,
)
from flowgraph.feature.moves import (
    blocked_feature,
    completed_feature,
    removed_feature,
    started_feature,
    unblocked_feature,
)
from flowgraph.feature.state import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureRemovedError,
    FeatureState,
    NoCriterionError,
    RemovedFeature,
    StartedFeature,
    make_feature,
    noted_feature,
)
from flowgraph.knowledge import UNMARKED, KnowledgeKind, Mark, make_knowledge_line
from flowgraph.parent import FeatureId, make_feature_id, parse_feature_id
from flowgraph.record import Now

# The states of a Feature live in state.py, its moves in moves.py and its file in file.py; they
# stay importable from here.
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

# The Feature of that id, whole; raises FeatureNotFoundError when the record holds none.
LoadFeature = Callable[[FeatureId], FeatureState]

# Save the Feature whole.
SaveFeature = Callable[[FeatureState], None]

# The ids of the Features in the record, as written; an empty list when it holds none.
FindFeatureIds = Callable[[], list[str]]


def next_feature_id(taken: Collection[FeatureId]) -> FeatureId:
    """The next free Feature id: one above the highest taken, the first when none is."""
    return make_feature_id(max((feature_id.number for feature_id in taken), default=0) + 1)


def note_feature(
    *,
    feature_id: FeatureId,
    kind: KnowledgeKind,
    text: str,
    load_feature: LoadFeature,
    save_feature: SaveFeature,
    now: Now,
    about: tuple[str, ...] = (),
    governs: tuple[str, ...] = (),
    mark: Mark = UNMARKED,
) -> None:
    """Keep a line of that kind and text on the Feature of that id, in any state, and save it.

    The line is about the terms given, governs the files given, carries the mark given and goes
    after the lines the Feature keeps. Raises
    FeatureNotFoundError when the record holds no such Feature and EmptyPartError when the text
    is blank; nothing is saved.
    """
    line = make_knowledge_line(kind, text, now(), about, governs, mark)
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
