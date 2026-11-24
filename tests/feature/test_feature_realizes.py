"""The criterion of a Feature a work item realizes: read at its place, from the Feature."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.feature import FeatureState, make_feature
from flowgraph.feature.realizes import criterion_at, realized_text
from flowgraph.parent import FeatureId, make_feature_id

pytestmark = pytest.mark.view

ONE = make_feature_id(1)
FEATURE = make_feature(
    ONE,
    "a feature title",
    ["a first criterion", "a second criterion"],
    "",
    datetime(2026, 1, 1, tzinfo=UTC),
)
CRITERIA = ("a first criterion", "a second criterion")


def held(feature_id: FeatureId) -> FeatureState:
    """The record of one Feature, F-0001."""
    assert feature_id == ONE
    return FEATURE


def never(_: FeatureId) -> Never:
    """A load that must not be called."""
    raise AssertionError("no Feature is loaded")


@pytest.mark.parametrize(("number", "text"), [(1, "a first criterion"), (2, "a second criterion")])
def test_the_criterion_at_a_place_of_the_list_is_its_text(number: int, text: str) -> None:
    assert criterion_at(CRITERIA, number) == text


@pytest.mark.parametrize("number", [3, 0])
def test_the_criterion_at_a_place_the_list_does_not_have_is_empty(number: int) -> None:
    assert criterion_at(CRITERIA, number) == ""


def test_the_text_realized_is_the_criterion_of_the_feature_held() -> None:
    assert realized_text(held, "F-0001", 2) == "a second criterion"


def test_the_text_realized_past_the_list_of_the_feature_is_empty() -> None:
    assert realized_text(held, "F-0001", 3) == ""


def test_the_text_realized_naming_no_criterion_is_empty_and_loads_nothing() -> None:
    assert realized_text(never, "F-0001", None) == ""


def test_the_text_realized_under_no_parent_is_empty_and_loads_nothing() -> None:
    assert realized_text(never, "", 2) == ""
