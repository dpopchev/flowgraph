"""The kind of a work item and its id: the kind names its noun and the prefix of the id."""

import pytest

from flowgraph.work_item import (
    KindError,
    WorkItemIdError,
    make_kind,
    make_work_item_id,
    next_work_item_id,
    parse_work_item_id,
    work_item_id_text,
)

pytestmark = pytest.mark.model

CHORE = make_kind("Chore", "a", "CH")
ERRAND = make_kind("Errand", "an", "ER")


def test_a_work_item_id_is_written_in_the_prefix_of_its_kind_and_four_digits() -> None:
    assert work_item_id_text(make_work_item_id(CHORE, 7)) == "CH-0007"


def test_a_work_item_id_below_one_is_refused_naming_its_kind() -> None:
    with pytest.raises(WorkItemIdError, match=r"^an Errand id counts from 1: 0 is below 1$"):
        make_work_item_id(ERRAND, 0)


def test_a_work_item_id_is_read_from_its_text() -> None:
    assert parse_work_item_id(CHORE, "CH-0012") == make_work_item_id(CHORE, 12)


def test_a_text_in_the_prefix_of_another_kind_is_refused_by_itself() -> None:
    with pytest.raises(
        WorkItemIdError, match=r"^'ER-0001' is no Chore id: it is CH- and a number$"
    ):
        parse_work_item_id(CHORE, "ER-0001")


def test_two_kinds_tell_apart_the_same_number() -> None:
    assert make_work_item_id(CHORE, 1) != make_work_item_id(ERRAND, 1)


def test_the_next_work_item_id_is_one_above_the_highest_taken() -> None:
    taken = [make_work_item_id(CHORE, 3), make_work_item_id(CHORE, 1)]
    assert next_work_item_id(CHORE, taken) == make_work_item_id(CHORE, 4)


def test_the_first_work_item_id_is_one() -> None:
    assert next_work_item_id(CHORE, []) == make_work_item_id(CHORE, 1)


@pytest.mark.parametrize("prefix", ["", "ch", "C-H", "C1"])
def test_a_prefix_that_is_not_capital_letters_is_refused(prefix: str) -> None:
    with pytest.raises(KindError, match=f"^{prefix!r} is no prefix: it is capital letters$"):
        make_kind("Chore", "a", prefix)


def test_a_kind_without_a_noun_is_refused() -> None:
    with pytest.raises(KindError, match=r"^a kind names its noun$"):
        make_kind(" ", "a", "CH")
