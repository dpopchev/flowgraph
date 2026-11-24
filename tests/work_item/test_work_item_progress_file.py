"""The progress lines of a work item in its file: a table each, read back whole, refused named."""

import tomllib
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import tomli_w

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    ProgressLine,
    ProgressRow,
    WorkItemFileError,
    WorkItemState,
    append_task,
    blocked_work_item,
    completed_task,
    completed_work_item,
    make_kind,
    make_progress_line,
    make_work_item,
    make_work_item_id,
    noted_work_item,
    progressed_work_item,
    read_work_item,
    read_work_item_detail,
    removed_work_item,
    started_task,
    started_work_item,
    work_item_detail,
    write_work_item,
)

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
BARE = make_work_item(make_work_item_id(CHORE, 1), "a title", SCENARIO, "", CREATED)
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ITEM = append_task(BARE, TASK)
HALF = started_task(started_work_item(ITEM, ON), make_task_id(3), ON)
STUCK = blocked_work_item(HALF, "no key", "developer", ON)
WHOLE = completed_work_item(completed_task(HALF, make_task_id(3), ON, COMMIT), ON, COMMIT)
REMOVED = removed_work_item(BARE, "a reason", ON)
FILE = Path("items") / "CH-0001.toml"


@pytest.fixture
def first() -> ProgressLine:
    """A progress line of the work item itself."""
    return make_progress_line("the first", ON)


@pytest.fixture
def of_task() -> ProgressLine:
    """A progress line of T-0003."""
    return make_progress_line("red: 1 failed", ON, make_task_id(3))


def held(tmp_path: Path) -> dict[str, Any]:
    """The file of CH-0001 as tomllib reads it."""
    return tomllib.loads((tmp_path / FILE).read_text("utf-8"))


def rewritten(tmp_path: Path, value: object, *keys: str | int) -> None:
    """Write the file of CH-0001 again by hand with the value at the end of the keys."""
    content = held(tmp_path)
    place: Any = content
    for key in keys[:-1]:
        place = place[key]
    place[keys[-1]] = value
    (tmp_path / FILE).write_text(tomli_w.dumps(content), "utf-8")


def test_a_progress_line_is_written_as_a_table_of_its_text_and_time(
    tmp_path: Path, first: ProgressLine
) -> None:
    write_work_item(tmp_path, progressed_work_item(BARE, first))
    assert held(tmp_path)["progress"] == [{"text": "the first", "noted": ON}]


def test_a_progress_line_of_a_task_is_written_with_its_task(
    tmp_path: Path, of_task: ProgressLine
) -> None:
    write_work_item(tmp_path, progressed_work_item(ITEM, of_task))
    assert held(tmp_path)["progress"][0]["task"] == "T-0003"


def test_a_work_item_with_no_progress_line_is_written_with_no_progress(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    assert "progress" not in held(tmp_path)


@pytest.mark.parametrize(
    ("item", "with_task"),
    [(ITEM, True), (HALF, True), (STUCK, True), (WHOLE, True), (REMOVED, False)],
    ids=["backlog", "started", "blocked", "completed", "removed"],
)
def test_a_work_item_with_progress_lines_reads_back_whole(
    tmp_path: Path,
    first: ProgressLine,
    of_task: ProgressLine,
    item: WorkItemState,
    with_task: bool,
) -> None:
    lines = (first, of_task) if with_task else (first,)
    for line in lines:
        item = progressed_work_item(item, line)
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, make_work_item_id(CHORE, 1)) == item


def test_the_detail_read_from_the_file_holds_the_progress_rows(
    tmp_path: Path, first: ProgressLine, of_task: ProgressLine
) -> None:
    write_work_item(tmp_path, progressed_work_item(progressed_work_item(HALF, first), of_task))
    assert read_work_item_detail(tmp_path, make_work_item_id(CHORE, 1)).progress == [
        ProgressRow(ON, "the first", ""),
        ProgressRow(ON, "red: 1 failed", "T-0003"),
    ]


def test_the_detail_of_the_work_item_holds_the_same_progress_rows(
    first: ProgressLine, of_task: ProgressLine
) -> None:
    item = progressed_work_item(progressed_work_item(HALF, first), of_task)
    assert work_item_detail(item).progress == [
        ProgressRow(ON, "the first", ""),
        ProgressRow(ON, "red: 1 failed", "T-0003"),
    ]


def test_a_work_item_with_a_finding_and_a_progress_line_reads_back_with_both(
    tmp_path: Path, first: ProgressLine
) -> None:
    noted = noted_work_item(BARE, make_knowledge_line(FINDING, "a fact", ON))
    item = progressed_work_item(noted, first)
    write_work_item(tmp_path, item)
    assert read_work_item(tmp_path, make_work_item_id(CHORE, 1)) == item


def test_a_file_whose_line_names_a_task_it_does_not_hold_is_refused(
    tmp_path: Path, of_task: ProgressLine
) -> None:
    write_work_item(tmp_path, progressed_work_item(ITEM, of_task))
    rewritten(tmp_path, "T-0009", "progress", 0, "task")
    with pytest.raises(WorkItemFileError, match="holds no Chore: no Task T-0009 in the record"):
        read_work_item(tmp_path, make_work_item_id(CHORE, 1))


def test_a_progress_table_that_holds_another_key_is_refused(
    tmp_path: Path, first: ProgressLine
) -> None:
    write_work_item(tmp_path, progressed_work_item(BARE, first))
    rewritten(tmp_path, "finding", "progress", 0, "kind")
    with pytest.raises(WorkItemFileError):
        read_work_item(tmp_path, make_work_item_id(CHORE, 1))


def test_a_progress_line_noted_with_no_offset_is_refused(
    tmp_path: Path, first: ProgressLine
) -> None:
    write_work_item(tmp_path, progressed_work_item(BARE, first))
    rewritten(tmp_path, date(2026, 10, 11), "progress", 0, "noted")
    with pytest.raises(WorkItemFileError, match="noted = 2026-10-11 is a time with no offset"):
        read_work_item(tmp_path, make_work_item_id(CHORE, 1))
