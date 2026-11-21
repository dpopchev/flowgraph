"""A completed Story in its file: written with its completed time and commit, read back whole."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.story import (
    StoryFileError,
    StoryRow,
    StoryState,
    append_task,
    completed_story,
    completed_task,
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
DONE = datetime(2026, 1, 3, 17, 45, 10, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
TASKS = [
    make_task(make_task_id(1), "a task title", "an output", "", CREATED),
    make_task(make_task_id(2), "another task title", "another output", "", CREATED),
]
STORY = append_task(
    append_task(make_story(make_story_id(1), "a title", SCENARIO, "", CREATED), TASKS[0]), TASKS[1]
)
BEGUN = started_task(started_story(STORY, ON), make_task_id(1), ON)
HALF = completed_task(BEGUN, make_task_id(1), DONE, make_commit("abc1234"))
WHOLE = completed_story(
    completed_task(
        started_task(HALF, make_task_id(2), ON), make_task_id(2), DONE, make_commit("bcd2345")
    ),
    DONE,
    make_commit("def5678"),
)
FILE = Path("items") / "ST-0001.toml"


def written(record: Path) -> dict[str, object]:
    """The file of ST-0001 in the record, as its primitives."""
    return tomllib.loads((record / FILE).read_text("utf-8"))


def test_a_completed_task_is_written_with_its_state_time_and_commit(tmp_path: Path) -> None:
    write_story(tmp_path, HALF)
    assert written(tmp_path)["tasks"] == [
        {
            "id": "T-0001",
            "state": "completed",
            "title": "a task title",
            "expected_output": "an output",
            "created": CREATED,
            "started": ON,
            "completed": DONE,
            "commit": "abc1234",
        },
        {
            "id": "T-0002",
            "state": "backlog",
            "title": "another task title",
            "expected_output": "another output",
            "created": CREATED,
        },
    ]


def test_a_completed_story_is_written_with_its_state_time_and_commit(tmp_path: Path) -> None:
    write_story(tmp_path, WHOLE)
    keys = ("state", "started", "completed", "commit")
    assert {key: written(tmp_path)[key] for key in keys} == {
        "state": "completed",
        "started": ON,
        "completed": DONE,
        "commit": "def5678",
    }


@pytest.mark.parametrize("story", [HALF, WHOLE], ids=["started-with-a-completed-task", "completed"])
def test_a_story_with_completed_items_is_read_back_whole(story: StoryState, tmp_path: Path) -> None:
    write_story(tmp_path, story)
    assert read_story(tmp_path, make_story_id(1)) == story


def test_a_completed_story_is_read_as_a_completed_row_with_its_commit(tmp_path: Path) -> None:
    write_story(tmp_path, WHOLE)
    assert read_story_rows(tmp_path) == [
        StoryRow("ST-0001", "a title", "completed", "def5678", created=CREATED)
    ]


def test_a_completed_story_is_read_as_detail_with_the_commit_of_each(tmp_path: Path) -> None:
    write_story(tmp_path, WHOLE)
    detail = read_story_detail(tmp_path, make_story_id(1))
    assert (detail.state, detail.commit, detail.tasks) == (
        "completed",
        "def5678",
        [
            TaskRow("T-0001", "a task title", "an output", "", "completed", "abc1234"),
            TaskRow("T-0002", "another task title", "another output", "", "completed", "bcd2345"),
        ],
    )


def test_a_completed_story_file_with_a_task_not_completed_is_refused(tmp_path: Path) -> None:
    write_story(tmp_path, WHOLE)
    text = (tmp_path / FILE).read_text("utf-8")
    (tmp_path / FILE).write_text(
        text.replace(
            'state = "completed"\ntitle = "another', 'state = "started"\ntitle = "another'
        ),
        encoding="utf-8",
    )
    with pytest.raises(StoryFileError, match=r"ST-0001\.toml holds no Story"):
        read_story(tmp_path, make_story_id(1))
