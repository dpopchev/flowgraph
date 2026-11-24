"""A work item file whose time holds no offset is refused when read, naming the file and the key."""

import re
import tomllib
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import tomli_w

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemFileError,
    WorkItemState,
    append_task,
    blocked_task,
    blocked_work_item,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    noted_work_item,
    read_work_item,
    read_work_item_detail,
    read_work_item_rows,
    removed_work_item,
    started_task,
    started_work_item,
    verified_work_item,
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
STUCK_TASK = blocked_task(HALF, make_task_id(3), "no key", "developer", ON)
WHOLE = completed_work_item(completed_task(HALF, make_task_id(3), ON, COMMIT), ON, COMMIT)
VERIFIED = verified_work_item(WHOLE, "it ran", ON)
REMOVED = removed_work_item(BARE, "a reason", ON)
NOTED = noted_work_item(BARE, make_knowledge_line(FINDING, "a line", ON))
FILE = Path("items") / "CH-0001.toml"
DAY = date(2026, 10, 11)
LINE = "is a time with no offset: write it with one, as 2026-01-01 09:00:00\\+00:00$"


def rewritten(path: Path, value: object, *keys: str | int) -> None:
    """Write the file again with the value at the end of the keys."""
    held = tomllib.loads(path.read_text("utf-8"))
    place: Any = held
    for key in keys[:-1]:
        place = place[key]
    place[keys[-1]] = value
    path.write_text(tomli_w.dumps(held), "utf-8")


def refusal(tmp_path: Path, key: str, written: str = "2026-10-11") -> str:
    """The whole line of the refusal of a time written with no offset in the file of CH-0001."""
    return f"^{re.escape(str(tmp_path / FILE))} holds no Chore: {key} = {re.escape(written)} {LINE}"


@pytest.mark.parametrize(
    ("item", "keys", "key"),
    [
        (BARE, ("created",), "created"),
        (ITEM, ("tasks", 0, "created"), "created"),
        (HALF, ("started",), "started"),
        (HALF, ("tasks", 0, "started"), "started"),
        (STUCK, ("since",), "since"),
        (STUCK_TASK, ("tasks", 0, "since"), "since"),
        (WHOLE, ("completed",), "completed"),
        (WHOLE, ("tasks", 0, "completed"), "completed"),
        (VERIFIED, ("verified", "on"), "on"),
        (REMOVED, ("removed",), "removed"),
        (NOTED, ("knowledge", 0, "noted"), "noted"),
    ],
)
def test_a_day_alone_in_the_file_is_refused_naming_the_file_and_the_key(
    tmp_path: Path, item: WorkItemState, keys: tuple[str | int, ...], key: str
) -> None:
    write_work_item(tmp_path, item)
    rewritten(tmp_path / FILE, DAY, *keys)
    with pytest.raises(WorkItemFileError, match=refusal(tmp_path, key) + "$"):
        read_work_item_rows(tmp_path, CHORE)


def test_a_work_item_read_by_its_id_is_refused_the_same_way(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    rewritten(tmp_path / FILE, DAY, "created")
    with pytest.raises(WorkItemFileError, match=refusal(tmp_path, "created") + "$"):
        read_work_item(tmp_path, make_work_item_id(CHORE, 1))


def test_a_work_item_read_in_detail_is_refused_the_same_way(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    rewritten(tmp_path / FILE, DAY, "created")
    with pytest.raises(WorkItemFileError, match=refusal(tmp_path, "created") + "$"):
        read_work_item_detail(tmp_path, make_work_item_id(CHORE, 1))


def test_a_time_with_no_offset_is_refused_naming_what_is_written(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    rewritten(tmp_path / FILE, datetime(2026, 10, 11, 9), "created")
    with pytest.raises(
        WorkItemFileError, match=refusal(tmp_path, "created", "2026-10-11 09:00:00")
    ):
        read_work_item_rows(tmp_path, CHORE)


def test_a_time_with_an_offset_is_read(tmp_path: Path) -> None:
    write_work_item(tmp_path, BARE)
    plus_two = datetime(2026, 10, 11, 9, tzinfo=timezone(timedelta(hours=2)))
    rewritten(tmp_path / FILE, plus_two, "created")
    assert read_work_item_rows(tmp_path, CHORE)[0].created == plus_two
