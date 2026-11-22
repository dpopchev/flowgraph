"""A Feature: a bigger outcome that groups work items, with the criteria the user experiences.

It is not worked on directly, so it holds no Task. Its state is its own, in Backlog or started,
as that of a work item is; the bucket a list shows it in is derived from the states of its work
items. It is kept as one file of the record, `items/F-0001.toml`.
"""

import tomllib
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from flowgraph.criterion import said
from flowgraph.item_file import write_checked
from flowgraph.parent import FeatureId, feature_id_text, make_feature_id, parse_feature_id
from flowgraph.record import ITEMS, Now
from flowgraph.task import StartedAlreadyError
from flowgraph.work_item import WorkItemRow

# The states of a Feature as the record writes them; a file without the line reads as in Backlog.
IN_BACKLOG = "backlog"
STARTED = "started"

# The states of a completed and of a removed work item, as the record writes them.
COMPLETED = "completed"
REMOVED = "removed"

# The states of a work item that leave nothing more to do on it.
DONE = frozenset({COMPLETED, REMOVED})

# The states of a work item that say work on it has begun.
BEGUN = frozenset({"started", COMPLETED})


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


# A Feature in any of its states, as the record keeps it.
FeatureState = Feature | StartedFeature


@dataclass
class FeatureDetail:
    """One Feature as plain data, as a view reads it from the record."""

    id: str
    title: str
    description: str
    criteria: list[str]


@dataclass
class FeatureRow:
    """One Feature as a line of a list reads it: its id, its title and its derived bucket.

    Its progress is the work items completed of those it holds; a removed one is not held. Its
    started work items are the rows a list writes under it, in the order given.
    """

    id: str
    title: str
    bucket: str
    completed: int
    held: int
    started: list[WorkItemRow] = field(default_factory=list[WorkItemRow], kw_only=True)


# The Feature of that id, whole; raises FeatureNotFoundError when the record holds none.
LoadFeature = Callable[[FeatureId], FeatureState]

# Save the Feature whole.
SaveFeature = Callable[[FeatureState], None]

# The ids of the Features in the record, as written; an empty list when it holds none.
FindFeatureIds = Callable[[], list[str]]


class NoCriterionError(ValueError):
    """A Feature without a criterion."""


class FeatureNotFoundError(Exception):
    """A record that holds no Feature of the id asked for."""

    def __init__(self, feature_id: FeatureId) -> None:
        super().__init__(f"no Feature {feature_id_text(feature_id)} in the record")


class FeatureFileError(Exception):
    """A file named as a Feature in a record that does not hold one; names its path."""


class FeatureMismatchError(Exception):
    """A Feature read back different from the one written; its file is as it was before."""


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

    Raises StartedAlreadyError when it is started.
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
        case _ as unreachable:
            assert_never(unreachable)


def _state_name(feature: FeatureState) -> str:
    """The state of a Feature as the record writes it."""
    match feature:
        case Feature():
            return IN_BACKLOG
        case StartedFeature():
            return STARTED
        case _ as unreachable:
            assert_never(unreachable)


def next_feature_id(taken: Collection[FeatureId]) -> FeatureId:
    """The next free Feature id: one above the highest taken, the first when none is."""
    return make_feature_id(max((feature_id.number for feature_id in taken), default=0) + 1)


def feature_detail(feature: FeatureState) -> FeatureDetail:
    """The Feature as the plain data a view reads."""
    return FeatureDetail(
        feature_id_text(feature.id), feature.title, feature.description, list(feature.criteria)
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


def feature_row(feature: FeatureState, states: Collection[str]) -> FeatureRow:
    """The Feature as the row a list reads, its bucket derived from the states of its work items.

    Its work items completed and held are counted from the same states, as the record writes them.
    """
    completed = sum(state == COMPLETED for state in states)
    held = sum(state != REMOVED for state in states)
    return FeatureRow(
        feature_id_text(feature.id), feature.title, bucket_of(states), completed, held
    )


def add_feature(
    *,
    title: str,
    criteria: Iterable[str],
    description: str,
    find_feature_ids: FindFeatureIds,
    save_feature: SaveFeature,
    now: Now,
) -> FeatureId:
    """Add a Feature under its next free id and return that id.

    Raises EmptyPartError when the title or a criterion is blank and NoCriterionError when it
    states none; nothing is saved.
    """
    taken = [parse_feature_id(text) for text in find_feature_ids()]
    feature = make_feature(next_feature_id(taken), title, criteria, description, now())
    save_feature(feature)
    return feature.id


class _FeatureFile(BaseModel):
    """What the file of a Feature in Backlog holds: no Task, and no time but its created one."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    created: datetime
    criteria: list[str]


class _StartedFeatureFile(BaseModel):
    """What the file of a started Feature holds: its started time too."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    created: datetime
    started: datetime
    criteria: list[str]


# The file of a Feature in any of its states.
_HeldFeatureFile = _FeatureFile | _StartedFeatureFile

# The validator of a Feature file, which tells the states apart by the state line.
_HELD_FEATURE: TypeAdapter[_HeldFeatureFile] = TypeAdapter(
    Annotated[_HeldFeatureFile, Field(discriminator="state")]
)


def feature_file(record: Path, feature_id: FeatureId) -> Path:
    """The path of the file of the Feature of that id in the record."""
    return record / ITEMS / f"{feature_id_text(feature_id)}.toml"


def _read_file(path: Path) -> FeatureState:
    """The Feature one file holds, built through its constructor and its moves.

    A file without a state line, as every one written before a Feature had a state, holds a
    Feature in Backlog. Raises FeatureFileError.
    """
    try:
        written = tomllib.loads(path.read_text(encoding="utf-8"))
        held = _HELD_FEATURE.validate_python({"state": IN_BACKLOG, **written})
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise FeatureFileError(f"{path} holds no Feature: {error}") from error
    feature = make_feature(
        parse_feature_id(held.id), held.title, held.criteria, held.description, held.created
    )
    match held:
        case _FeatureFile():
            return feature
        case _StartedFeatureFile():
            return started_feature(feature, held.started)
        case _ as unreachable:
            assert_never(unreachable)


def _moves_primitives(feature: FeatureState) -> dict[str, object]:
    """The times of the moves a Feature has made, as its file holds them."""
    match feature:
        case Feature():
            return {}
        case StartedFeature():
            return {"started": feature.started}
        case _ as unreachable:
            assert_never(unreachable)


def read_feature(record: Path, feature_id: FeatureId) -> FeatureState:
    """Adapter: the Feature of that id in the record, whole.

    Raises FeatureNotFoundError when the record holds no such Feature and FeatureFileError when
    its file does not hold one.
    """
    path = feature_file(record, feature_id)
    if not path.is_file():
        raise FeatureNotFoundError(feature_id)
    return _read_file(path)


def read_feature_ids(record: Path) -> list[str]:
    """Adapter: the ids of the Features in the record, as their files are named, in no order."""
    return [path.stem for path in (record / ITEMS).glob("F-*.toml")]


def write_feature(record: Path, feature: FeatureState) -> None:
    """Adapter: write the Feature as its one file in the record, its state line in it.

    It is written beside its file and read back before it replaces it. Raises
    FeatureMismatchError naming the file when the Feature read back differs; the file is then
    as it was before.
    """
    path = feature_file(record, feature.id)
    described = {"description": feature.description} if feature.description else {}
    primitives = {
        "id": feature_id_text(feature.id),
        "state": _state_name(feature),
        "title": feature.title,
        **described,
        "created": feature.created,
        **_moves_primitives(feature),
        "criteria": list(feature.criteria),
    }
    write_checked(
        path,
        primitives,
        lambda beside: _read_file(beside) == feature,
        FeatureMismatchError(f"{path}: the Feature written reads back different"),
    )
