"""The knowledge a work item keeps: a line noted in any state, in order, read back whole."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import EmptyPartError, make_scenario
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    make_kind,
    make_work_item,
    make_work_item_id,
    note_work_item,
    noted_work_item,
    read_work_item,
    read_work_item_detail,
    removed_work_item,
    started_work_item,
    write_work_item,
)

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
FIRST = make_knowledge_line(FINDING, "the first", ON)
SECOND = make_knowledge_line(FINDING, "the second", ON)
ID = make_work_item_id(CHORE, 1)
BARE = make_work_item(ID, "a title", make_scenario("a", "b", "c"), "", CREATED)
TASKED = append_task(BARE, make_task(make_task_id(1), "a task title", "an output", "", CREATED))
STARTED = started_work_item(TASKED, ON)
REMOVED = removed_work_item(BARE, "a reason", ON)


@pytest.mark.parametrize("item", [BARE, STARTED, REMOVED], ids=["backlog", "started", "removed"])
def test_a_line_noted_in_any_state_is_read_back_whole(tmp_path: Path, item: WorkItemState) -> None:
    noted = noted_work_item(noted_work_item(item, FIRST), SECOND)
    write_work_item(tmp_path, noted)
    assert read_work_item(tmp_path, ID).knowledge == (FIRST, SECOND)


def test_a_line_is_kept_after_the_lines_noted_before_it() -> None:
    assert noted_work_item(noted_work_item(BARE, FIRST), SECOND).knowledge == (FIRST, SECOND)


def test_the_detail_read_from_the_file_lists_the_lines_by_kind_time_and_text(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, noted_work_item(BARE, FIRST))
    detail = read_work_item_detail(tmp_path, ID)
    assert [(row.kind, row.noted, row.text) for row in detail.knowledge] == [
        ("finding", ON, "the first")
    ]


def test_a_blank_text_is_refused_and_nothing_is_saved() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(EmptyPartError, match=r"^text is empty$"):
        note_work_item(
            item_id=ID,
            kind=FINDING,
            text=" ",
            load_work_item=lambda _: BARE,
            save_work_item=saved.append,
            now=lambda: ON,
        )
    assert saved == []
