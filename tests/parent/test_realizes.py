"""The criterion a work item realizes: a place counted from 1 or none, asked and checked."""

import pytest

from flowgraph.parent import STANDALONE, FeatureId
from flowgraph.parent.realizes import (
    NO_CRITERION,
    CriterionPlace,
    RealizesError,
    make_criterion_place,
    realizes_asked,
    realizes_number,
    realizes_under,
    realizes_written,
)

pytestmark = pytest.mark.model


def test_a_place_from_1_is_made() -> None:
    assert make_criterion_place(2) == CriterionPlace(2)


def test_a_place_below_1_is_refused_naming_it() -> None:
    with pytest.raises(RealizesError, match=r"^a criterion is counted from 1: 0 is below 1$"):
        make_criterion_place(0)


def test_no_text_given_asks_for_nothing() -> None:
    assert realizes_asked(None) is None


def test_the_word_none_asks_for_no_criterion() -> None:
    assert realizes_asked("none") == NO_CRITERION


def test_digits_ask_for_the_place_they_make() -> None:
    assert realizes_asked("2") == CriterionPlace(2)


def test_digits_that_make_0_are_refused_as_a_place_below_1() -> None:
    with pytest.raises(RealizesError, match=r"^a criterion is counted from 1: 0 is below 1$"):
        realizes_asked("0")


@pytest.mark.parametrize("text", ["two", "", "-1", "1.5"])
def test_any_other_text_is_refused_naming_it(text: str) -> None:
    with pytest.raises(
        RealizesError,
        match=rf"^--realizes {text!r} is neither the number of a criterion nor none$",
    ):
        realizes_asked(text)


def test_a_file_without_a_number_is_read_as_no_criterion() -> None:
    assert realizes_written(None) == NO_CRITERION


def test_a_file_holding_a_number_is_read_as_its_place() -> None:
    assert realizes_written(2) == CriterionPlace(2)


def test_no_criterion_is_written_as_no_number() -> None:
    assert realizes_number(NO_CRITERION) is None


def test_a_place_is_written_as_its_number() -> None:
    assert realizes_number(CriterionPlace(2)) == 2


def test_a_place_under_a_feature_is_kept() -> None:
    assert realizes_under(CriterionPlace(2), FeatureId(1)) == CriterionPlace(2)


def test_no_criterion_under_a_feature_is_kept() -> None:
    assert realizes_under(NO_CRITERION, FeatureId(1)) == NO_CRITERION


def test_no_criterion_standing_alone_is_kept() -> None:
    assert realizes_under(NO_CRITERION, STANDALONE) == NO_CRITERION


def test_a_place_standing_alone_is_refused() -> None:
    with pytest.raises(
        RealizesError,
        match=(
            r"^--realizes names a criterion of the Feature a work item is under: "
            r"this one stands alone$"
        ),
    ):
        realizes_under(CriterionPlace(2), STANDALONE)
