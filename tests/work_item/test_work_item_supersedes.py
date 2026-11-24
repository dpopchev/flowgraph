"""The lines a line of a work item supersedes: kept on it in its file, read back whole."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.knowledge import DECISION, line_ref, make_knowledge_line
from flowgraph.work_item import (
    WorkItemState,
    make_kind,
    make_work_item,
    make_work_item_id,
    note_work_item,
    noted_work_item,
    read_work_item,
    read_work_item_detail,
    work_item_path,
    write_work_item,
)

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_work_item_id(CHORE, 1)
BARE = make_work_item(ID, "a title", make_scenario("a", "b", "c"), "", CREATED)
FIRST = make_knowledge_line(DECISION, "keep one store", ON)
SECOND = make_knowledge_line(
    DECISION, "keep one file per item", ON, supersedes=(line_ref("CH-0001", 1),)
)
BOTH = noted_work_item(noted_work_item(BARE, FIRST), SECOND)


def first_table(record: Path) -> dict[str, object]:
    """The table of the first line of the file of the item, read with tomllib."""
    held = tomllib.loads(work_item_path(record, ID).read_text(encoding="utf-8"))
    return held["knowledge"][0]


def test_an_item_with_a_line_that_supersedes_another_is_read_back_equal(tmp_path: Path) -> None:
    write_work_item(tmp_path, BOTH)
    assert read_work_item(tmp_path, ID) == BOTH


def test_the_detail_read_from_the_file_holds_the_refs_the_line_supersedes(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, BOTH)
    assert read_work_item_detail(tmp_path, ID).knowledge[1].supersedes == ["CH-0001#1"]


def test_the_table_of_the_first_line_is_left_as_written_when_a_later_supersedes_it(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, noted_work_item(BARE, FIRST))
    before = first_table(tmp_path)
    write_work_item(tmp_path, BOTH)
    assert first_table(tmp_path) == before


def test_the_table_of_a_line_that_supersedes_none_holds_no_key_supersedes(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, BOTH)
    assert "supersedes" not in first_table(tmp_path)


def test_a_note_that_supersedes_a_line_saves_an_item_whose_last_line_holds_it() -> None:
    saved: list[WorkItemState] = []
    note_work_item(
        item_id=ID,
        kind=DECISION,
        text="a text",
        load_work_item=lambda _: BARE,
        save_work_item=saved.append,
        now=lambda: ON,
        supersedes=("CH-0001#1",),
    )
    assert saved[0].knowledge[-1].supersedes == ("CH-0001#1",)
