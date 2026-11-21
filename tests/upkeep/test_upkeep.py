"""An Upkeep in Backlog: its id counts per kind, and every part that must say something does."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.story import make_scenario
from flowgraph.upkeep import (
    UpkeepIdError,
    make_upkeep,
    make_upkeep_id,
    next_upkeep_id,
    parse_upkeep_id,
    upkeep_id_text,
)

pytestmark = pytest.mark.model

SCENARIO = make_scenario("a behavior", "it runs", "it still holds")
CREATED = datetime(2026, 1, 1, 12, 30, 15, 500, tzinfo=UTC)


def test_an_upkeep_id_is_written_u_and_four_digits_at_least() -> None:
    assert upkeep_id_text(make_upkeep_id(7)) == "U-0007"


def test_an_upkeep_id_below_one_is_refused() -> None:
    with pytest.raises(UpkeepIdError, match=r"^an Upkeep id counts from 1: 0 is below 1$"):
        make_upkeep_id(0)


def test_an_upkeep_id_is_read_from_its_text() -> None:
    assert parse_upkeep_id("U-0012") == make_upkeep_id(12)


def test_a_text_that_is_no_upkeep_id_is_refused_by_itself() -> None:
    with pytest.raises(UpkeepIdError, match=r"^'ST-0001' is no Upkeep id: it is U- and a number$"):
        parse_upkeep_id("ST-0001")


def test_the_next_upkeep_id_is_one_above_the_highest_taken() -> None:
    assert next_upkeep_id([make_upkeep_id(3), make_upkeep_id(1)]) == make_upkeep_id(4)


def test_the_first_upkeep_id_is_one() -> None:
    assert next_upkeep_id([]) == make_upkeep_id(1)


def test_a_blank_title_is_refused_by_name() -> None:
    with pytest.raises(EmptyPartError, match=r"^title is empty$"):
        make_upkeep(make_upkeep_id(1), " ", SCENARIO, "", CREATED)


def test_the_created_time_is_kept_to_the_second() -> None:
    made = make_upkeep(make_upkeep_id(1), "a title", SCENARIO, "", CREATED)
    assert made.created == CREATED.replace(microsecond=0)
