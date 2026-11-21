"""A started Story as a view reads it: its row and its detail name the state of each item."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import (
    StoryRow,
    append_task,
    make_story,
    make_story_id,
    started_story,
    started_task,
    story_detail,
    story_row,
)
from flowgraph.task import TaskRow, make_task, make_task_id

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
BARE = make_story(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
STORY = append_task(
    append_task(BARE, make_task(make_task_id(1), "a task", "an output", "", CREATED)),
    make_task(make_task_id(2), "another task", "another output", "", CREATED),
)
STARTED = started_task(started_story(STORY, CREATED), make_task_id(1), CREATED)


def test_a_started_story_reads_as_a_started_row() -> None:
    tasks = [
        TaskRow("T-0001", "a task", "an output", "", "started"),
        TaskRow("T-0002", "another task", "another output", "", "backlog"),
    ]
    assert story_row(STARTED) == StoryRow(
        "S-0001", "a title", "started", created=CREATED, started=CREATED, tasks=tasks
    )


def test_a_started_story_reads_as_detail_with_the_state_of_each_task() -> None:
    detail = story_detail(STARTED)
    assert (detail.state, detail.tasks) == (
        "started",
        [
            TaskRow("T-0001", "a task", "an output", "", "started"),
            TaskRow("T-0002", "another task", "another output", "", "backlog"),
        ],
    )
