"""The criterion of a Feature a work item realizes: the text at its place, read from the Feature."""

from collections.abc import Sequence
from typing import assert_never

from flowgraph.feature.model import LoadFeature
from flowgraph.parent import (
    CriterionPlace,
    FeatureId,
    NoCriterion,
    Parent,
    Realizes,
    RealizesError,
    Standalone,
    feature_id_text,
    parse_feature_id,
)


def criterion_at(criteria: Sequence[str], number: int) -> str:
    """The criterion at that place counted from 1; empty when the list has none there."""
    return criteria[number - 1] if 1 <= number <= len(criteria) else ""


def realized_text(load_feature: LoadFeature, parent: str, realizes: int | None) -> str:
    """The text of the criterion a work item under that parent realizes.

    Empty when it names none or has no parent, and then no Feature is loaded, and empty when the
    Feature has no criterion there. Raises FeatureNotFoundError when the record holds no
    Feature of that id.
    """
    if realizes is None or not parent:
        return ""
    return criterion_at(load_feature(parse_feature_id(parent)).criteria, realizes)


def check_realized(load_feature: LoadFeature, parent: Parent, realizes: Realizes) -> None:
    """Check that the Feature the work item is under has the criterion it names.

    No criterion, or standing alone, asks nothing and loads no Feature. Raises
    FeatureNotFoundError when the record holds no such Feature and RealizesError naming the
    Feature and the count of its criteria when it has none at that place.
    """
    match realizes:
        case NoCriterion():
            return
        case CriterionPlace(number=number):
            match parent:
                case Standalone():
                    return
                case FeatureId():
                    criteria = load_feature(parent).criteria
                    if not criterion_at(criteria, number):
                        raise RealizesError(
                            f"{feature_id_text(parent)} has no criterion {number}: "
                            f"its criteria count from 1 to {len(criteria)}"
                        )
                case _ as unreachable:
                    assert_never(unreachable)
        case _ as unreachable:
            assert_never(unreachable)
