"""Starting a Story and its Tasks: a Story starts with a Task, a Task under a started Story."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import (
    StartedStory,
    append_task,
    make_story,
    make_story_id,
    started_story,
    started_task,
)
from flowgraph.task import (
    ItemInBacklogError,
    NoTaskError,
    StartedAlreadyError,
    StartedTask,
    TaskNotFoundError,
    make_task,
    make_task_id,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, 500, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
BARE = make_story(make_story_id(1), "a title", SCENARIO, "why", CREATED)
TASK = make_task(make_task_id(1), "a task title", "an output", "how", CREATED)
STORY = append_task(BARE, TASK)


def test_a_story_with_a_task_starts_on_the_second_with_its_task_in_backlog() -> None:
    assert started_story(STORY, ON) == StartedStory(
        id=make_story_id(1),
        title="a title",
        scenario=SCENARIO,
        description="why",
        created=CREATED,
        started=ON.replace(microsecond=0),
        tasks=(TASK,),
    )


def test_a_story_without_a_task_is_refused_by_its_id() -> None:
    with pytest.raises(NoTaskError, match=r"^ST-0001 has no Task to start with$"):
        started_story(BARE, ON)


def test_a_started_story_is_refused_by_its_id() -> None:
    with pytest.raises(StartedAlreadyError, match=r"^ST-0001 is started already$"):
        started_story(started_story(STORY, ON), ON)


def test_a_task_of_a_started_story_starts_on_the_second() -> None:
    assert started_task(started_story(STORY, ON), make_task_id(1), ON).tasks == (
        StartedTask(
            id=make_task_id(1),
            title="a task title",
            expected_output="an output",
            description="how",
            created=CREATED,
            started=ON.replace(microsecond=0),
        ),
    )


def test_a_task_starts_alone_among_the_tasks_of_its_story() -> None:
    second = make_task(make_task_id(2), "another task title", "another output", "", CREATED)
    begun = started_story(append_task(STORY, second), ON)
    assert started_task(begun, make_task_id(2), ON).tasks[0] == TASK


def test_a_task_of_a_story_in_backlog_is_refused_naming_both() -> None:
    with pytest.raises(ItemInBacklogError, match=r"^T-0001 cannot start: ST-0001 is in Backlog$"):
        started_task(STORY, make_task_id(1), ON)


def test_a_started_task_is_refused_by_its_id() -> None:
    begun = started_task(started_story(STORY, ON), make_task_id(1), ON)
    with pytest.raises(StartedAlreadyError, match=r"^T-0001 is started already$"):
        started_task(begun, make_task_id(1), ON)


def test_a_task_the_story_does_not_hold_is_refused_by_its_id() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0002 in the record$"):
        started_task(started_story(STORY, ON), make_task_id(2), ON)
