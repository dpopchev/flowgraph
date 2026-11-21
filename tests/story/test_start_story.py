"""Starting a Story or a Task: the Story that holds it is loaded, started now and saved whole."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import (
    StoryState,
    append_task,
    make_story,
    make_story_id,
    parse_story_id,
    started_story,
    started_task,
    story_id_text,
)
from flowgraph.task import TaskNotFoundError, make_task, make_task_id
from flowgraph.work_item import holder_of, start_task, start_work_item

pytestmark = pytest.mark.command

NOW = datetime(2026, 1, 2, tzinfo=UTC)
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
SCENARIO = make_scenario("a", "b", "c")


def story(number: int, task: int) -> StoryState:
    """A Story in Backlog of that number, holding one Task of that number."""
    bare = make_story(make_story_id(number), "a title", SCENARIO, "", CREATED)
    return append_task(bare, make_task(make_task_id(task), "a task", "an output", "", CREATED))


def test_a_started_story_is_saved_whole_started_now() -> None:
    saved: list[StoryState] = []
    start_work_item(
        item_id=make_story_id(1),
        load_work_item=lambda _: story(1, 1),
        save_work_item=saved.append,
        now=lambda: NOW,
    )
    assert saved == [started_story(story(1, 1), NOW)]


RECORD = {
    story_id_text(held.id): held
    for held in (started_story(story(1, 1), NOW), started_story(story(2, 2), NOW))
}


def start(task: int, saved: list[StoryState]) -> object:
    """Start the Task of that number in a record of two started Stories, one Task each."""
    return start_task(
        task_id=make_task_id(task),
        load_holder=lambda task_id: holder_of(
            task_id,
            [parse_story_id(key) for key in RECORD],
            lambda story_id: RECORD[story_id_text(story_id)],
        ),
        save_work_item=saved.append,
        now=lambda: NOW,
    )


def test_a_started_task_returns_the_id_of_the_story_that_holds_it() -> None:
    assert start(2, []) == make_story_id(2)


def test_a_started_task_saves_its_story_whole_with_the_task_started_now() -> None:
    saved: list[StoryState] = []
    start(2, saved)
    assert saved == [started_task(RECORD["ST-0002"], make_task_id(2), NOW)]


def test_a_task_no_story_holds_is_refused_by_its_id() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0003 in the record$"):
        start(3, [])
