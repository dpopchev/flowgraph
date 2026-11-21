"""The parent of a work item: the Feature it is under, or standing alone.

Containment is a typed reference: a work item names its Feature by id and never holds it.
"""

import re
from dataclasses import dataclass
from typing import assert_never


@dataclass(frozen=True)
class FeatureId:
    """The identity of a Feature: its number in the record, written `F-0001`."""

    number: int


@dataclass(frozen=True)
class Standalone:
    """A work item under no Feature: standing alone is a value of parent, not a missing one."""


# The one value of standing alone.
STANDALONE = Standalone()

# What a work item is under: a Feature, named by its id, or nothing.
Parent = FeatureId | Standalone


class FeatureIdError(ValueError):
    """A number or a text that is no Feature id."""


def make_feature_id(number: int) -> FeatureId:
    """The id of the Feature with that number; raises FeatureIdError when it is below 1."""
    if number < 1:
        raise FeatureIdError(f"a Feature id counts from 1: {number} is below 1")
    return FeatureId(number)


def feature_id_text(feature_id: FeatureId) -> str:
    """The id as it is written: `F-` and the number, at least four digits."""
    return f"F-{feature_id.number:04d}"


def parse_feature_id(text: str) -> FeatureId:
    """The id written as the text; raises FeatureIdError when it is not `F-` and a number."""
    written = re.fullmatch(r"F-(\d+)", text)
    if written is None:
        raise FeatureIdError(f"{text!r} is no Feature id: it is F- and a number")
    return make_feature_id(int(written.group(1)))


def parent_text(parent: Parent) -> str:
    """The parent as it is written: the id of its Feature, or nothing for standing alone."""
    match parent:
        case FeatureId():
            return feature_id_text(parent)
        case Standalone():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def parent_written(text: str) -> Parent:
    """The parent written as the text: standing alone for nothing, else the Feature of that id.

    Raises FeatureIdError when the text is neither.
    """
    return parse_feature_id(text) if text else STANDALONE
