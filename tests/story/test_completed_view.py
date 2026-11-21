"""A completed Story as a view reads it: its row and its detail carry the commit of each item."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.story import (
    StoryRow,
    append_task,
    completed_story,
    completed_task,
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
STORY = append_task(BARE, make_task(make_task_id(1), "a task", "an output", "", CREATED))
BEGUN = started_task(started_story(STORY, CREATED), make_task_id(1), CREATED)
HALF = completed_task(BEGUN, make_task_id(1), CREATED, make_commit("abc1234"))
WHOLE = completed_story(HALF, CREATED, make_commit("def5678"))
DONE = [TaskRow("T-0001", "a task", "an output", "", "completed", "abc1234")]


def test_a_completed_story_reads_as_a_completed_row_with_its_commit() -> None:
    assert story_row(WHOLE) == StoryRow(
        "S-0001", "a title", "completed", "def5678", created=CREATED, completed=CREATED, tasks=DONE
    )


def test_a_story_not_completed_reads_as_a_row_without_a_commit() -> None:
    assert story_row(HALF) == StoryRow(
        "S-0001", "a title", "started", "", created=CREATED, started=CREATED, tasks=DONE
    )


def test_a_completed_story_reads_as_detail_with_the_commit_of_each() -> None:
    detail = story_detail(WHOLE)
    assert (detail.state, detail.commit, detail.tasks) == (
        "completed",
        "def5678",
        [TaskRow("T-0001", "a task", "an output", "", "completed", "abc1234")],
    )
