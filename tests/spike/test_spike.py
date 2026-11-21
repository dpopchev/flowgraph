"""A Spike in Backlog: its id counts per kind, and it states a hypothesis."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.branch import branch_of, make_slug
from flowgraph.criterion import CriterionError, Hypothesis, make_hypothesis, make_scenario
from flowgraph.spike import (
    SPIKE,
    SpikeIdError,
    make_spike,
    make_spike_id,
    next_spike_id,
    parse_spike_id,
    spike_id_text,
)
from flowgraph.store import KINDS

pytestmark = pytest.mark.model

QUESTION = make_hypothesis("Can one file per item hold the record?")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)


def test_a_spike_id_is_written_q_and_four_digits_at_least() -> None:
    assert spike_id_text(make_spike_id(7)) == "Q-0007"


def test_a_spike_id_below_one_is_refused() -> None:
    with pytest.raises(SpikeIdError, match=r"^a Spike id counts from 1: 0 is below 1$"):
        make_spike_id(0)


def test_a_spike_id_is_read_from_its_text() -> None:
    assert parse_spike_id("Q-0012") == make_spike_id(12)


def test_a_text_that_is_no_spike_id_is_refused_by_itself() -> None:
    with pytest.raises(SpikeIdError, match=r"^'S-0001' is no Spike id: it is Q- and a number$"):
        parse_spike_id("S-0001")


def test_a_text_written_sp_and_a_number_is_no_spike_id() -> None:
    with pytest.raises(SpikeIdError, match=r"^'SP-0001' is no Spike id: it is Q- and a number$"):
        parse_spike_id("SP-0001")


def test_the_branch_of_a_spike_is_named_by_its_q_id_and_slug() -> None:
    assert branch_of(make_spike_id(1), make_slug("one-file"), Path("/src/project")).name == (
        "wi/Q-0001-one-file"
    )


def test_the_next_spike_id_is_one_above_the_highest_taken() -> None:
    assert next_spike_id([make_spike_id(3), make_spike_id(1)]) == make_spike_id(4)


def test_a_spike_states_its_hypothesis() -> None:
    assert make_spike(make_spike_id(1), "a title", QUESTION, "", CREATED).criterion == Hypothesis(
        "Can one file per item hold the record?"
    )


def test_a_spike_with_a_given_when_then_is_refused() -> None:
    with pytest.raises(
        CriterionError, match=r"^a Spike states a hypothesis, not a Given / When / Then$"
    ):
        make_spike(make_spike_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)


def test_the_spike_is_one_of_the_kinds_a_record_holds() -> None:
    assert SPIKE in KINDS
