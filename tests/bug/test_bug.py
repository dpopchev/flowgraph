"""A Bug in Backlog: its id counts per kind, and it states what is observed and expected."""

from datetime import UTC, datetime

import pytest

from flowgraph.bug import (
    BUG,
    BugIdError,
    bug_id_text,
    make_bug,
    make_bug_id,
    next_bug_id,
    parse_bug_id,
)
from flowgraph.criterion import CriterionError, Defect, make_defect, make_scenario
from flowgraph.record.store import KINDS

pytestmark = pytest.mark.model

DEFECT = make_defect("it prints a traceback", "it exits 2")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)


def test_a_bug_id_is_written_b_and_four_digits_at_least() -> None:
    assert bug_id_text(make_bug_id(7)) == "B-0007"


def test_a_bug_id_below_one_is_refused() -> None:
    with pytest.raises(BugIdError, match=r"^a Bug id counts from 1: 0 is below 1$"):
        make_bug_id(0)


def test_a_bug_id_is_read_from_its_text() -> None:
    assert parse_bug_id("B-0012") == make_bug_id(12)


def test_a_text_that_is_no_bug_id_is_refused_by_itself() -> None:
    with pytest.raises(BugIdError, match=r"^'S-0001' is no Bug id: it is B- and a number$"):
        parse_bug_id("S-0001")


def test_the_next_bug_id_is_one_above_the_highest_taken() -> None:
    assert next_bug_id([make_bug_id(3), make_bug_id(1)]) == make_bug_id(4)


def test_a_bug_states_what_is_observed_and_expected() -> None:
    assert make_bug(make_bug_id(1), "a title", DEFECT, "", CREATED).criterion == Defect(
        "it prints a traceback", "it exits 2"
    )


def test_a_bug_with_a_given_when_then_is_refused() -> None:
    with pytest.raises(
        CriterionError,
        match=r"^a Bug states what is observed and expected, not a Given / When / Then$",
    ):
        make_bug(make_bug_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)


def test_the_bug_is_one_of_the_kinds_a_record_holds() -> None:
    assert BUG in KINDS
