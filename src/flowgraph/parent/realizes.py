"""The criterion of its Feature a work item realizes: the place of one counted from 1, or none.

Naming none is a value, as standing alone is one of the parent: a work item is never given a
missing place.
"""

import re
from dataclasses import dataclass
from typing import assert_never

from flowgraph.parent.model import NONE, Parent, Standalone


@dataclass(frozen=True)
class CriterionPlace:
    """The place of one criterion of a Feature, counted from 1."""

    number: int


@dataclass(frozen=True)
class NoCriterion:
    """A work item naming no criterion of its Feature: a value of realizes, not a missing one."""


# The one value of naming none.
NO_CRITERION = NoCriterion()

# What a work item names of the criteria of its Feature: one of them by its place, or none.
Realizes = CriterionPlace | NoCriterion


class RealizesError(ValueError):
    """A place that is below 1, a text that is no place, or a place given to a work item alone."""


def make_criterion_place(number: int) -> CriterionPlace:
    """The place of the criterion with that number; raises RealizesError when it is below 1."""
    if number < 1:
        raise RealizesError(f"a criterion is counted from 1: {number} is below 1")
    return CriterionPlace(number)


def realizes_asked(text: str | None) -> Realizes | None:
    """The criterion a command asks for: none when it was not given, `none` for no criterion,
    else the place the digits make.

    Raises RealizesError when the text is neither digits nor `none`, and for a place below 1.
    """
    if text is None:
        return None
    if text == NONE:
        return NO_CRITERION
    if re.fullmatch(r"\d+", text) is None:
        raise RealizesError(f"--realizes {text!r} is neither the number of a criterion nor none")
    return make_criterion_place(int(text))


def realizes_written(number: int | None) -> Realizes:
    """The criterion a file holds: none for no number, else the place of that number."""
    return NO_CRITERION if number is None else make_criterion_place(number)


def realizes_number(realizes: Realizes) -> int | None:
    """The number a file holds for the criterion: none for no criterion, else the place."""
    match realizes:
        case CriterionPlace():
            return realizes.number
        case NoCriterion():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def realizes_under(realizes: Realizes, parent: Parent) -> Realizes:
    """The criterion, once checked against the parent; raises RealizesError for a place given to
    a work item standing alone.
    """
    if isinstance(realizes, CriterionPlace) and isinstance(parent, Standalone):
        raise RealizesError(
            "--realizes names a criterion of the Feature a work item is under: "
            "this one stands alone"
        )
    return realizes
