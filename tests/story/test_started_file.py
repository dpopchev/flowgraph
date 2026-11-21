"""A started Story in its file: written with its started time, read back whole and as plain data."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import (
    StoryFileError,
    StoryRow,
    append_task,
    make_story,
    make_story_id,
    read_story,
    read_story_detail,
    read_story_rows,
    started_story,
    started_task,
    write_story,
)
from flowgraph.task import TaskRow, make_task, make_task_id

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
TASKS = [
    make_task(make_task_id(1), "a task title", "an output", "", CREATED),
    make_task(make_task_id(2), "another task title", "another output", "", CREATED),
]
STORY = append_task(
    append_task(make_story(make_story_id(1), "a title", SCENARIO, "", CREATED), TASKS[0]), TASKS[1]
)
STARTED = started_task(started_story(STORY, ON), make_task_id(1), ON)
FILE = Path("items") / "ST-0001.toml"


def written(record: Path) -> dict[str, object]:
    """The file of ST-0001 in the record, as its primitives."""
    return tomllib.loads((record / FILE).read_text("utf-8"))


def test_a_started_story_is_written_with_its_state_and_started_time(tmp_path: Path) -> None:
    write_story(tmp_path, STARTED)
    assert {key: written(tmp_path)[key] for key in ("state", "started")} == {
        "state": "started",
        "started": ON,
    }


def test_a_started_task_is_written_with_its_state_and_started_time(tmp_path: Path) -> None:
    write_story(tmp_path, STARTED)
    assert written(tmp_path)["tasks"] == [
        {
            "id": "T-0001",
            "state": "started",
            "title": "a task title",
            "expected_output": "an output",
            "created": CREATED,
            "started": ON,
        },
        {
            "id": "T-0002",
            "state": "backlog",
            "title": "another task title",
            "expected_output": "another output",
            "created": CREATED,
        },
    ]


def test_a_started_story_is_read_back_whole(tmp_path: Path) -> None:
    write_story(tmp_path, STARTED)
    assert read_story(tmp_path, make_story_id(1)) == STARTED


def test_a_started_story_is_read_as_a_started_row(tmp_path: Path) -> None:
    write_story(tmp_path, STARTED)
    assert read_story_rows(tmp_path) == [StoryRow("ST-0001", "a title", "started", created=CREATED)]


def test_a_started_story_is_read_as_detail_with_the_state_of_each_task(tmp_path: Path) -> None:
    write_story(tmp_path, STARTED)
    detail = read_story_detail(tmp_path, make_story_id(1))
    assert (detail.state, detail.tasks) == (
        "started",
        [
            TaskRow("T-0001", "a task title", "an output", "", "started"),
            TaskRow("T-0002", "another task title", "another output", "", "backlog"),
        ],
    )


STARTED_TASK = (
    '[[tasks]]\nid = "T-0001"\nstate = "started"\ntitle = "t"\nexpected_output = "o"\n'
    "created = 2026-01-01T12:30:15Z\nstarted = 2026-01-02T09:00:00Z\n"
)


@pytest.mark.parametrize(
    ("state", "tasks"),
    [('state = "started"\n', ""), ('state = "backlog"\n', STARTED_TASK)],
    ids=["started-story-without-its-time", "backlog-story-with-a-started-task"],
)
def test_a_state_without_the_fields_it_needs_is_refused_naming_the_file(
    state: str, tasks: str, tmp_path: Path
) -> None:
    head = 'id = "ST-0001"\ntitle = "a title"\ncreated = 2026-01-01T12:30:15Z\n'
    criterion = '[criterion]\ngiven = "a"\nwhen = "b"\nthen = "c"\n'
    (tmp_path / "items").mkdir()
    (tmp_path / FILE).write_text(head + state + criterion + tasks, encoding="utf-8")
    with pytest.raises(StoryFileError, match=r"ST-0001\.toml holds no Story"):
        read_story(tmp_path, make_story_id(1))
