"""The id of a Task: a number from 1, written `T-0001`, the next one above the highest taken."""

import pytest

from flowgraph.task import TaskIdError, make_task_id, next_task_id, parse_task_id, task_id_text

pytestmark = pytest.mark.model


def test_the_first_id_is_written_with_four_digits() -> None:
    assert task_id_text(make_task_id(1)) == "T-0001"


def test_a_number_below_one_is_no_id() -> None:
    with pytest.raises(TaskIdError, match="0 is below 1"):
        make_task_id(0)


def test_the_next_id_of_a_record_with_no_tasks_is_the_first() -> None:
    assert next_task_id([]) == make_task_id(1)


def test_the_next_id_is_one_above_the_highest_taken() -> None:
    assert next_task_id([make_task_id(3), make_task_id(1)]) == make_task_id(4)


def test_a_written_id_is_read_back() -> None:
    assert parse_task_id("T-0012") == make_task_id(12)


@pytest.mark.parametrize("text", ["ST-0001", "T-", "T-one", "0001"])
def test_a_text_of_another_form_is_no_id(text: str) -> None:
    with pytest.raises(TaskIdError, match=f"{text!r} is no Task id"):
        parse_task_id(text)
