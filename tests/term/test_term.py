"""A term: its constructor. A name is lowercase words joined by `-`; a meaning says something."""

import re
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.term import KINDS, Term, TermError, make_term, relate

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


def test_the_kinds_of_relation_are_is_a_and_part_of() -> None:
    assert KINDS == ("is-a", "part-of")


def test_a_term_has_no_relation_when_it_is_made() -> None:
    assert make_term("gate", MEANING, ADDED).part_of == ()


def test_a_term_related_with_part_of_holds_the_other_as_its_whole() -> None:
    assert relate(make_term("gate", MEANING, ADDED), "part-of", "lane").part_of == ("lane",)


def test_a_term_related_with_is_a_holds_the_other_as_its_kind() -> None:
    assert relate(make_term("gate", MEANING, ADDED), "is-a", "check").is_a == ("check",)


def test_a_term_related_keeps_its_name_its_meaning_and_its_time() -> None:
    gate = make_term("gate", MEANING, ADDED)
    assert relate(gate, "part-of", "lane").meaning == gate.meaning


def test_a_kind_outside_the_set_is_refused_naming_the_two() -> None:
    with pytest.raises(
        TermError, match=re.escape("'owns' is no kind of relation: is-a or part-of")
    ):
        relate(make_term("gate", MEANING, ADDED), "owns", "lane")


def test_a_term_related_to_itself_is_refused() -> None:
    with pytest.raises(TermError, match=re.escape("gate cannot be part-of itself")):
        relate(make_term("gate", MEANING, ADDED), "part-of", "gate")


def test_a_relation_kept_already_is_refused() -> None:
    gate = relate(make_term("gate", MEANING, ADDED), "part-of", "lane")
    with pytest.raises(TermError, match=re.escape("gate is part-of lane already")):
        relate(gate, "part-of", "lane")
