"""The file of a Feature: one file of the record, `items/F-0001.toml`, read and written whole.

Its state line tells the states apart, and each state holds the times and the texts of the moves
that reached it, no other (`flowgraph.feature.held_file`). A Feature is built from its file
through its constructor and its moves (`flowgraph.feature.state`, `flowgraph.feature.moves`).
"""

import tomllib
from dataclasses import replace
from pathlib import Path
from typing import assert_never

from pydantic import ValidationError

from flowgraph.criterion import CommitError, EmptyPartError, Evidence, evidence_written
from flowgraph.feature.held_file import (
    HELD_FEATURE,
    BlockedFeatureFile,
    CompletedFeatureFile,
    FeatureFile,
    HeldFeatureFile,
    RemovedFeatureFile,
    StartedFeatureFile,
)
from flowgraph.feature.moves import (
    blocked_feature,
    completed_feature,
    removed_feature,
    started_feature,
)
from flowgraph.feature.state import (
    IN_BACKLOG,
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureState,
    NoCriterionError,
    RemovedFeature,
    StartedFeature,
    make_feature,
    state_name,
)
from flowgraph.item import (
    NoOffsetError,
    evidence_primitives,
    knowledge_held,
    knowledge_primitives,
    write_checked,
)
from flowgraph.item.file_refusal import file_refusal
from flowgraph.parent import FeatureId, FeatureIdError, feature_id_text, parse_feature_id
from flowgraph.record import ITEMS


class FeatureNotFoundError(Exception):
    """A record that holds no Feature of the id asked for."""

    def __init__(self, feature_id: FeatureId) -> None:
        super().__init__(f"no Feature {feature_id_text(feature_id)} in the record")


class FeatureFileError(Exception):
    """A file named as a Feature in a record that does not hold one; names its path."""


class FeatureMismatchError(Exception):
    """A Feature read back different from the one written; its file is as it was before."""


def feature_file(record: Path, feature_id: FeatureId) -> Path:
    """The path of the file of the Feature of that id in the record."""
    return record / ITEMS / f"{feature_id_text(feature_id)}.toml"


def _read_file(path: Path) -> FeatureState:
    """The Feature one file holds, built through its constructor and its moves.

    A file without a state line, as every one written before a Feature had a state, holds a
    Feature in Backlog. Raises FeatureFileError, for a commit that is no sha too, and for a part
    its constructor or its moves refuse, as a blank reason; a key or a state the model does not
    take is refused in one line, the first such error; a time with no offset is refused so.
    """
    try:
        written = tomllib.loads(path.read_text(encoding="utf-8"))
        held = HELD_FEATURE.validate_python({"state": IN_BACKLOG, **written})
        commit = evidence_written(held.commit if isinstance(held, CompletedFeatureFile) else "")
    except ValidationError as error:
        raise FeatureFileError(
            f"{path} holds no Feature: {file_refusal(error, tagged=True)}"
        ) from error
    except (tomllib.TOMLDecodeError, CommitError, NoOffsetError) as error:
        raise FeatureFileError(f"{path} holds no Feature: {error}") from error
    try:
        built = _built(held, commit)
        lines = tuple(knowledge_held(line) for line in held.knowledge)
        return replace(built, knowledge=lines, about=tuple(held.about))
    except (EmptyPartError, NoCriterionError, FeatureIdError) as error:
        raise FeatureFileError(f"{path} holds no Feature: {error}") from error


def _built(held: HeldFeatureFile, commit: Evidence) -> FeatureState:
    """The Feature the content of a file holds, through its constructor and its moves.

    Raises the refusal of the constructor or of a move.
    """
    feature = make_feature(
        parse_feature_id(held.id), held.title, held.criteria, held.description, held.created
    )
    match held:
        case FeatureFile():
            return feature
        case StartedFeatureFile():
            return started_feature(feature, held.started)
        case BlockedFeatureFile():
            begun = started_feature(feature, held.started)
            return blocked_feature(begun, held.reason, held.waiting_on, held.since)
        case CompletedFeatureFile():
            return completed_feature(started_feature(feature, held.started), held.completed, commit)
        case RemovedFeatureFile():
            return removed_feature(feature, held.reason, held.removed)
        case _ as unreachable:
            assert_never(unreachable)


def _moves_primitives(feature: FeatureState) -> dict[str, object]:
    """What the moves a Feature has made left it, as its file holds it: times, a commit, reasons."""
    match feature:
        case Feature():
            return {}
        case StartedFeature():
            return {"started": feature.started}
        case BlockedFeature():
            block = {"reason": feature.reason, "waiting_on": feature.waiting_on}
            return {"started": feature.started, "since": feature.since, **block}
        case CompletedFeature():
            times = {"started": feature.started, "completed": feature.completed}
            return {**times, **evidence_primitives(feature.commit)}
        case RemovedFeature():
            return {"removed": feature.removed, "reason": feature.reason}
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
    lines = [knowledge_primitives(line) for line in feature.knowledge]
    knowledge = {"knowledge": lines} if lines else {}
    about = {"about": list(feature.about)} if feature.about else {}
    primitives = {
        "id": feature_id_text(feature.id),
        "state": state_name(feature),
        "title": feature.title,
        **described,
        **about,
        "created": feature.created,
        **_moves_primitives(feature),
        "criteria": list(feature.criteria),
        **knowledge,
    }
    write_checked(
        path,
        primitives,
        lambda beside: _read_file(beside) == feature,
        FeatureMismatchError(f"{path}: the Feature written reads back different"),
    )
