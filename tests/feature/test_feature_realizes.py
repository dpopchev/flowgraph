"""The criterion of a Feature a work item realizes: read at its place, from the Feature."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.feature import FeatureState, make_feature
from flowgraph.feature.realizes import check_realized, criterion_at, realized_text
from flowgraph.parent import (
    NO_CRITERION,
    STANDALONE,
    CriterionPlace,
    FeatureId,
    Parent,
    Realizes,
    RealizesError,
    make_feature_id,
)

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


def test_a_place_the_feature_has_passes_the_check() -> None:
    assert check_realized(held, ONE, CriterionPlace(2)) is None


def test_a_place_past_the_end_is_refused_naming_the_feature_and_the_count() -> None:
    with pytest.raises(
        RealizesError, match=r"^F-0001 has no criterion 3: its criteria count from 1 to 2$"
    ):
        check_realized(held, ONE, CriterionPlace(3))


@pytest.mark.parametrize(
    ("parent", "realizes"),
    [(ONE, NO_CRITERION), (STANDALONE, NO_CRITERION), (STANDALONE, CriterionPlace(2))],
    ids=["no-criterion", "no-criterion-alone", "alone"],
)
def test_the_check_loads_no_feature_for_no_criterion_or_no_parent(
    parent: Parent, realizes: Realizes
) -> None:
    assert check_realized(never, parent, realizes) is None
