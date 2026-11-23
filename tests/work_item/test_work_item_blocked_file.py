"""The file of a blocked work item: its block written, read back whole and read as a row."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemFileError,
    append_task,
    blocked_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    read_work_item_rows,
    started_task,
    started_work_item,
    unblocked_work_item,
    work_item_detail,
    work_item_row,
    write_work_item,
)
from flowgraph.work_item.agent import Agent
from flowgraph.work_item.handed import handed_work_item

pytestmark = pytest.mark.edge

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)
SINCE = datetime(2026, 1, 3, 9, 0, 0, 500, tzinfo=UTC)
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)
OTHER = make_task(make_task_id(2), "another task", "an output", "", CREATED)
ITEM = append_task(
    append_task(make_work_item(ONE, "a title", make_scenario("a", "b", "c"), "", CREATED), TASK),
    OTHER,
)
STARTED = started_task(
    handed_work_item(started_work_item(ITEM, ON), Agent("sonnet-a1")), make_task_id(1), ON
)
BLOCKED = blocked_work_item(STARTED, "no key", "developer", SINCE)
FILE = Path("items") / "CH-0001.toml"
WRITTEN_BEFORE = (
    'id = "CH-0001"\n'
    'title = "a title"\n'
    "created = 2026-01-01 12:30:15+00:00\n"
    "started = 2026-01-02 08:00:00+00:00\n"
    "since = 2026-01-03 09:00:00+00:00\n"
    'waiting_on = "developer"\n'
    "[criterion]\n"
    'given = "a"\nwhen = "b"\nthen = "c"\n'
    "[[tasks]]\n"
    'id = "T-0001"\nstate = "backlog"\ntitle = "a task title"\nexpected_output = "an output"\n'
    "created = 2026-01-01 12:30:15+00:00\n"
)


def keep(tmp_path: Path, content: str) -> None:
    """Write the content as the file of CH-0001 in the record at tmp_path."""
    (tmp_path / "items").mkdir()
    (tmp_path / FILE).write_text(content, "utf-8")


def written(tmp_path: Path) -> dict[str, object]:
    """What the file of CH-0001 in the record at tmp_path holds."""
    return tomllib.loads((tmp_path / FILE).read_text("utf-8"))


def test_a_blocked_work_item_is_written_with_its_started_time_its_agent_and_its_block_in_order(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, BLOCKED)
    assert list(written(tmp_path)) == [
        "id",
        "state",
        "title",
        "created",
        "started",
        "agent",
        "since",
        "reason",
        "waiting_on",
        "criterion",
        "tasks",
    ]


def test_a_blocked_work_item_is_written_with_its_state_line_and_its_block(tmp_path: Path) -> None:
    write_work_item(tmp_path, BLOCKED)
    held = written(tmp_path)
    assert [held[key] for key in ("state", "since", "reason", "waiting_on")] == [
        "blocked",
        SINCE.replace(microsecond=0),
        "no key",
        "developer",
    ]


def test_a_blocked_work_item_reads_back_whole(tmp_path: Path) -> None:
    write_work_item(tmp_path, BLOCKED)
    assert read_work_item(tmp_path, ONE) == BLOCKED


def test_the_block_leaves_the_file_of_a_work_item_at_its_unblock(tmp_path: Path) -> None:
    write_work_item(tmp_path, STARTED)
    was = written(tmp_path)
    write_work_item(tmp_path, BLOCKED)
    write_work_item(tmp_path, unblocked_work_item(BLOCKED))
    assert written(tmp_path) == was


def test_a_blocked_file_with_a_blank_reason_is_refused_naming_it(tmp_path: Path) -> None:
    keep(tmp_path, f'state = "blocked"\nreason = " "\n{WRITTEN_BEFORE}')
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml holds no Chore: reason is empty$"):
        read_work_item(tmp_path, ONE)


def test_a_file_with_a_blank_title_is_refused_naming_it(tmp_path: Path) -> None:
    keep(
        tmp_path,
        'id = "CH-0001"\nstate = "backlog"\ntitle = " "\ncreated = 2026-01-01 12:30:15+00:00\n'
        '[criterion]\ngiven = "a"\nwhen = "b"\nthen = "c"\n',
    )
    with pytest.raises(WorkItemFileError, match=r"CH-0001\.toml holds no Chore: title is empty$"):
        read_work_item(tmp_path, ONE)


def test_the_row_read_from_the_file_of_a_blocked_work_item_is_the_row_of_it(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, BLOCKED)
    assert read_work_item_rows(tmp_path, CHORE) == [work_item_row(BLOCKED)]


def test_the_row_of_a_blocked_work_item_holds_its_block() -> None:
    row = work_item_row(BLOCKED)
    assert (row.started, row.block_reason, row.waiting_on, row.reason) == (
        ON,
        "no key",
        "developer",
        "",
    )


def test_the_detail_read_from_the_file_holds_its_reason_and_what_it_waits_on(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, BLOCKED)
    detail = read_work_item_detail(tmp_path, ONE)
    assert (detail.state, detail.reason, detail.waiting_on) == ("blocked", "no key", "developer")


def test_the_detail_of_a_blocked_work_item_holds_its_reason_and_what_it_waits_on() -> None:
    detail = work_item_detail(BLOCKED)
    assert (detail.state, detail.reason, detail.waiting_on) == ("blocked", "no key", "developer")
