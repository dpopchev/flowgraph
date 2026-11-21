"""Writing a Task: it takes the next free Task id of the record and its Story is saved whole."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import StoryState, add_task, append_task, make_story, make_story_id
from flowgraph.task import make_task, make_task_id

pytestmark = pytest.mark.command

NOW = datetime(2026, 1, 1, tzinfo=UTC)
STORY = make_story(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", NOW)


def add(saved: list[StoryState]) -> object:
    """Write one Task for ST-0001 in a record whose highest Task id is T-0003."""
    return add_task(
        parent="ST-0001",
        title="a task title",
        expected_output="an output",
        description="",
        load_story=lambda _: STORY,
        find_task_ids=lambda: ["T-0003", "T-0001"],
        save_story=saved.append,
        now=lambda: NOW,
    )


def test_it_returns_the_next_free_task_id_of_the_record() -> None:
    assert add([]) == make_task_id(4)


def test_it_saves_the_story_whole_with_the_task_created_now() -> None:
    saved: list[StoryState] = []
    add(saved)
    task = make_task(make_task_id(4), "a task title", "an output", "", NOW)
    assert saved == [append_task(STORY, task)]
