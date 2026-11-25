"""The progress line of an item by its id: kept on its work item, a Task named, or refused."""

import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import EmptyPartError, make_scenario
from flowgraph.item.commands import ItemIdError, Written
from flowgraph.item.progress import ProgressLineError, note_progress
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import TaskNotFoundError, make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    make_progress_line,
    make_work_item,
    progressed_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
BEGUN = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)
ON = datetime(2026, 1, 3, 9, 0, 0, tzinfo=UTC)
TASK = make_task(make_task_id(1), "a task", "an output", "", CREATED)
STORY_ITEM = append_task(
    make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED), TASK
)
STARTED = started_task(started_work_item(STORY_ITEM, BEGUN), make_task_id(1), BEGUN)
NOT_KNOWLEDGE = "a progress line takes no --about and no --governs: it is no knowledge line"
NO_FEATURE = (
    "F-0001 keeps no progress line: fgraph note --progress takes a work item or a Task of it"
)


def never(*_: object) -> Never:
    """A read or a write of the record that a progress line never asks for."""
    raise AssertionError("a progress line reads and saves the work items alone")


def store(items: Sequence[WorkItemState], saved: list[WorkItemState]) -> Store:
    """The store of a record holding those Stories, which notes what it saves."""
    held = {item.id: item for item in items}
    return Store(
        find_work_item_rows=lambda kind: (
            [work_item_row(item) for item in items] if kind == STORY else []
        ),
        load_work_item=held.__getitem__,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=saved.append,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def test_a_progress_line_of_a_work_item_says_its_id_and_the_message_of_its_commit() -> None:
    written = note_progress("S-0001", "a text", store([STARTED], []), lambda: ON)
    assert written == Written("noted S-0001\n", "chore: note S-0001 in the record")


def test_a_progress_line_of_a_work_item_is_saved_on_it() -> None:
    saved: list[WorkItemState] = []
    note_progress("S-0001", "a text", store([STARTED], saved), lambda: ON)
    assert saved == [progressed_work_item(STARTED, make_progress_line("a text", ON))]


def test_a_progress_line_of_a_task_is_saved_on_its_work_item_naming_the_task() -> None:
    saved: list[WorkItemState] = []
    written = note_progress("T-0001", "a text", store([STARTED], saved), lambda: ON)
    line = make_progress_line("a text", ON, make_task_id(1))
    assert (written, saved) == (
        Written("noted T-0001 of S-0001\n", "chore: note T-0001 of S-0001 in the record"),
        [progressed_work_item(STARTED, line)],
    )


def test_a_blank_progress_line_is_refused() -> None:
    with pytest.raises(EmptyPartError):
        note_progress("S-0001", " ", store([STARTED], []), lambda: ON)


def test_a_blank_progress_line_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(EmptyPartError):
        note_progress("S-0001", " ", store([STARTED], saved), lambda: ON)
    assert saved == []


@pytest.mark.parametrize(
    ("item", "about", "governs", "line"),
    [
        ("F-0001", None, None, NO_FEATURE),
        ("S-0001", ["gate"], None, NOT_KNOWLEDGE),
        ("S-0001", None, ["a.py"], NOT_KNOWLEDGE),
    ],
    ids=["a-feature", "about", "governs"],
)
def test_a_progress_line_asked_for_what_it_does_not_take_is_refused(
    item: str, about: list[str] | None, governs: list[str] | None, line: str
) -> None:
    with pytest.raises(ProgressLineError, match=f"^{re.escape(line)}$"):
        note_progress(item, "a text", store([STARTED], []), lambda: ON, about, governs)


def test_a_progress_line_of_a_task_the_record_does_not_hold_is_refused() -> None:
    with pytest.raises(TaskNotFoundError):
        note_progress("T-0009", "a text", store([STARTED], []), lambda: ON)


def test_a_progress_line_of_a_text_that_is_no_id_is_refused() -> None:
    with pytest.raises(ItemIdError):
        note_progress("nope", "a text", store([STARTED], []), lambda: ON)


@pytest.mark.parametrize("mark", ["standing", "open"])
def test_a_progress_line_given_a_mark_is_refused_naming_its_option(mark: str) -> None:
    line = f"a progress line takes no --{mark}: it is no knowledge line"
    with pytest.raises(ProgressLineError, match=f"^{re.escape(line)}$"):
        note_progress("S-0001", "a text", store([STARTED], []), lambda: ON, mark=mark)


def test_a_progress_line_given_a_mark_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(ProgressLineError):
        note_progress("S-0001", "a text", store([STARTED], saved), lambda: ON, mark="standing")
    assert saved == []


def test_a_progress_line_of_a_task_given_a_mark_is_refused_naming_its_option() -> None:
    line = "a progress line takes no --standing: it is no knowledge line"
    with pytest.raises(ProgressLineError, match=f"^{re.escape(line)}$"):
        note_progress("T-0001", "a text", store([STARTED], []), lambda: ON, mark="standing")
