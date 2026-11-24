"""The criterion of a Feature a work item realizes: the text at its place, read from the Feature."""

from collections.abc import Sequence

from flowgraph.feature.model import LoadFeature
from flowgraph.parent import parse_feature_id


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
