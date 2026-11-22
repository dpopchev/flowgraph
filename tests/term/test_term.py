"""A term: its constructor. A name is lowercase words joined by `-`; a meaning says something."""

import re
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.term import Term, TermError, make_term

pytestmark = pytest.mark.model

ADDED = datetime(2026, 1, 1, tzinfo=UTC)
MEANING = "a check every deliverable passes before it lands"


def test_a_term_holds_its_name_its_meaning_and_the_time_it_was_added() -> None:
    assert make_term("gate", MEANING, ADDED) == Term("gate", MEANING, ADDED)


@pytest.mark.parametrize("name", ["gate", "work-item", "v2", "a-1-b", "2fa"])
def test_a_name_of_lowercase_words_of_letters_and_digits_joined_by_a_dash_is_kept(
    name: str,
) -> None:
    assert make_term(name, MEANING, ADDED).name == name


@pytest.mark.parametrize(
    "name",
    ["", "Gate", "work item", "-gate", "gate-", "work--item", "work_item", "gate!"],
    ids=[
        "empty",
        "capital",
        "space",
        "leading-dash",
        "trailing-dash",
        "double-dash",
        "under",
        "bang",
    ],
)
def test_a_name_that_is_not_lowercase_words_joined_by_a_dash_is_refused_by_name(
    name: str,
) -> None:
    with pytest.raises(TermError, match=rf"^{name!r} is no term name: lowercase words"):
        make_term(name, MEANING, ADDED)


@pytest.mark.parametrize("name", ["F-0001", "S-0001", "T-0290", "s-0001"])
def test_a_name_that_reads_as_the_id_of_an_item_is_refused_by_name(name: str) -> None:
    with pytest.raises(TermError, match=rf"^{name!r} reads as the id of an item"):
        make_term(name, MEANING, ADDED)


@pytest.mark.parametrize("meaning", ["", "  ", "\n"], ids=["empty", "spaces", "newline"])
def test_a_blank_meaning_is_refused_naming_the_part(meaning: str) -> None:
    with pytest.raises(EmptyPartError, match=re.escape("meaning is empty")):
        make_term("gate", meaning, ADDED)
