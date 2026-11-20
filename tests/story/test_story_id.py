"""The id of a Story: a number from 1, written `ST-0001`, the next one above the highest taken."""

import pytest

from flowgraph.story import (
    StoryIdError,
    make_story_id,
    next_story_id,
    parse_story_id,
    story_id_text,
)

pytestmark = pytest.mark.model


def test_the_first_id_is_written_with_four_digits() -> None:
    assert story_id_text(make_story_id(1)) == "ST-0001"


def test_a_number_below_one_is_no_id() -> None:
    with pytest.raises(StoryIdError, match="0 is below 1"):
        make_story_id(0)


def test_the_next_id_of_an_empty_record_is_the_first() -> None:
    assert next_story_id([]) == make_story_id(1)


def test_the_next_id_is_one_above_the_highest_taken() -> None:
    assert next_story_id([make_story_id(3), make_story_id(1)]) == make_story_id(4)


def test_a_written_id_is_read_back() -> None:
    assert parse_story_id("ST-0012") == make_story_id(12)


@pytest.mark.parametrize("text", ["B-0001", "ST-", "ST-one", "0001"])
def test_a_text_of_another_form_is_no_id(text: str) -> None:
    with pytest.raises(StoryIdError, match=f"{text!r} is no Story id"):
        parse_story_id(text)
