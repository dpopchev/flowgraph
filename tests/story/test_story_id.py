"""The id of a Story: a number from 1, written `S-0001`, the next one above the highest taken."""

from pathlib import Path

import pytest

from flowgraph.development import branch_of, make_slug
from flowgraph.story import (
    StoryIdError,
    make_story_id,
    next_story_id,
    parse_story_id,
    story_id_text,
)

pytestmark = pytest.mark.model


def test_the_first_id_is_written_with_four_digits() -> None:
    assert story_id_text(make_story_id(1)) == "S-0001"


def test_a_number_below_one_is_no_id() -> None:
    with pytest.raises(StoryIdError, match="0 is below 1"):
        make_story_id(0)


def test_the_next_id_of_an_empty_record_is_the_first() -> None:
    assert next_story_id([]) == make_story_id(1)


def test_the_next_id_is_one_above_the_highest_taken() -> None:
    assert next_story_id([make_story_id(3), make_story_id(1)]) == make_story_id(4)


def test_a_written_id_is_read_back() -> None:
    assert parse_story_id("S-0012") == make_story_id(12)


@pytest.mark.parametrize("text", ["B-0001", "S-", "S-one", "0001"])
def test_a_text_of_another_form_is_no_id(text: str) -> None:
    with pytest.raises(StoryIdError, match=f"{text!r} is no Story id"):
        parse_story_id(text)


def test_a_text_written_st_and_a_number_is_no_story_id() -> None:
    with pytest.raises(StoryIdError, match=r"^'ST-0001' is no Story id: it is S- and a number$"):
        parse_story_id("ST-0001")


def test_the_branch_of_a_story_is_named_by_its_s_id_and_slug() -> None:
    assert branch_of(make_story_id(1), make_slug("one-file"), Path("/src/project")).name == (
        "wi/S-0001-one-file"
    )
