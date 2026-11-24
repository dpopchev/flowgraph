"""The id of a Task: its number in the record, written `T-0001`."""

import re
from collections.abc import Collection
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskId:
    """The identity of a Task: its number in the record, written `T-0001`."""

    number: int


class TaskIdError(ValueError):
    """A number or a text that is no Task id."""


def make_task_id(number: int) -> TaskId:
    """The id of the Task with that number in the record.

    Raises TaskIdError when the number is below 1.
    """
    if number < 1:
        raise TaskIdError(f"a Task id counts from 1: {number} is below 1")
    return TaskId(number)


def task_id_text(task_id: TaskId) -> str:
    """The id as it is written: `T-` and the number, at least four digits."""
    return f"T-{task_id.number:04d}"


def parse_task_id(text: str) -> TaskId:
    """The id written as the text.

    Raises TaskIdError when the text is not `T-` and a number.
    """
    written = re.fullmatch(r"T-(\d+)", text)
    if written is None:
        raise TaskIdError(f"{text!r} is no Task id: it is T- and a number")
    return make_task_id(int(written.group(1)))


def next_task_id(taken: Collection[TaskId]) -> TaskId:
    """The next free id: one above the highest taken, the first when none is."""
    return make_task_id(max((task_id.number for task_id in taken), default=0) + 1)
