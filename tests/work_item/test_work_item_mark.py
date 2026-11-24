"""The mark of a line of a work item: kept in its file, read back whole, refused if wrong."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.knowledge import FINDING, OPEN, STANDING, Mark, make_knowledge_line
from flowgraph.work_item import (
    WorkItemFileError,
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


@pytest.mark.parametrize("mark", [STANDING, OPEN], ids=["standing", "open"])
def test_a_line_with_a_mark_is_read_back_equal(tmp_path: Path, mark: Mark) -> None:
    line = make_knowledge_line(FINDING, "a text", ON, mark=mark)
    write_work_item(tmp_path, noted_work_item(BARE, line))
    assert read_work_item(tmp_path, ID).knowledge == (line,)


def test_the_detail_read_from_the_file_holds_the_mark_of_the_line(tmp_path: Path) -> None:
    line = make_knowledge_line(FINDING, "a text", ON, mark=OPEN)
    write_work_item(tmp_path, noted_work_item(BARE, line))
    assert read_work_item_detail(tmp_path, ID).knowledge[0].mark == "open"


def test_the_table_of_a_line_with_no_mark_holds_no_key_mark(tmp_path: Path) -> None:
    write_work_item(tmp_path, noted_work_item(BARE, make_knowledge_line(FINDING, "a text", ON)))
    held = tomllib.loads(work_item_path(tmp_path, ID).read_text(encoding="utf-8"))
    assert "mark" not in held["knowledge"][0]


def test_a_file_with_a_word_that_is_no_mark_is_refused_when_read(tmp_path: Path) -> None:
    line = make_knowledge_line(FINDING, "a text", ON, mark=OPEN)
    write_work_item(tmp_path, noted_work_item(BARE, line))
    path = work_item_path(tmp_path, ID)
    path.write_text(
        path.read_text(encoding="utf-8").replace('mark = "open"', 'mark = "fact"'),
        encoding="utf-8",
    )
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml"):
        read_work_item(tmp_path, ID)


def test_a_note_with_a_mark_saves_an_item_whose_last_line_holds_it() -> None:
    saved: list[WorkItemState] = []
    note_work_item(
        item_id=ID,
        kind=FINDING,
        text="a text",
        load_work_item=lambda _: BARE,
        save_work_item=saved.append,
        now=lambda: ON,
        mark=OPEN,
    )
    assert saved[0].knowledge[-1].mark == OPEN
