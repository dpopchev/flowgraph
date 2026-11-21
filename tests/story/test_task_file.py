"""The Tasks in the file of a Story: written inside it, read back whole, by id or as plain data."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import (
    StoryNotFoundError,
    append_task,
    make_story,
    make_story_id,
    read_story,
    read_story_detail,
    read_task_ids,
    story_detail,
    write_story,
)
from flowgraph.task import make_task, make_task_id

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
STORY = make_story(make_story_id(1), "a title", SCENARIO, "", CREATED)
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)


def written_tasks(record: Path) -> object:
    """The tasks table of the file of ST-0001 in the record."""
    return tomllib.loads((record / "items" / "ST-0001.toml").read_text("utf-8"))["tasks"]


def test_a_task_is_written_inside_the_file_of_its_story(tmp_path: Path) -> None:
    write_story(tmp_path, append_task(STORY, TASK))
    assert written_tasks(tmp_path) == [
        {
            "id": "T-0001",
            "state": "backlog",
            "title": "a task title",
            "expected_output": "an output",
            "created": CREATED,
        }
    ]


def test_the_description_of_a_task_is_written_when_there_is_one(tmp_path: Path) -> None:
    described = make_task(make_task_id(1), "a task title", "an output", "how", CREATED)
    write_story(tmp_path, append_task(STORY, described))
    assert written_tasks(tmp_path) == [
        {
            "id": "T-0001",
            "state": "backlog",
            "title": "a task title",
            "description": "how",
            "expected_output": "an output",
            "created": CREATED,
        }
    ]


def test_a_written_story_is_read_back_whole_with_its_tasks(tmp_path: Path) -> None:
    write_story(tmp_path, append_task(STORY, TASK))
    assert read_story(tmp_path, make_story_id(1)) == append_task(STORY, TASK)


def test_a_story_the_record_does_not_hold_is_refused_by_its_id(tmp_path: Path) -> None:
    write_story(tmp_path, STORY)
    with pytest.raises(StoryNotFoundError, match=r"^no Story ST-0002 in the record$"):
        read_story(tmp_path, make_story_id(2))


def test_the_task_ids_of_a_record_are_those_of_every_story(tmp_path: Path) -> None:
    another = make_story(make_story_id(2), "another title", SCENARIO, "", CREATED)
    second = make_task(make_task_id(2), "another task title", "another output", "", CREATED)
    write_story(tmp_path, append_task(STORY, TASK))
    write_story(tmp_path, append_task(another, second))
    assert sorted(read_task_ids(tmp_path)) == ["T-0001", "T-0002"]


def test_a_written_story_is_read_as_its_detail(tmp_path: Path) -> None:
    described = make_story(make_story_id(1), "a title", SCENARIO, "why", CREATED)
    task = make_task(make_task_id(1), "a task title", "an output", "how", CREATED)
    write_story(tmp_path, append_task(described, task))
    assert read_story_detail(tmp_path, make_story_id(1)) == story_detail(
        append_task(described, task)
    )


def test_the_detail_of_a_story_the_record_does_not_hold_is_refused(tmp_path: Path) -> None:
    with pytest.raises(StoryNotFoundError, match=r"^no Story ST-0001 in the record$"):
        read_story_detail(tmp_path, make_story_id(1))
