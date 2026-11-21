"""The detail of a Story: its criterion and its Tasks as the plain data `fgraph show` reads."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import StoryDetail, append_task, make_story, make_story_id, story_detail
from flowgraph.task import TaskRow, make_task, make_task_id

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")


def test_a_story_reads_as_its_detail_with_its_tasks() -> None:
    story = append_task(
        make_story(make_story_id(1), "a title", SCENARIO, "why", CREATED),
        make_task(make_task_id(2), "a task title", "an output", "how", CREATED),
    )
    assert story_detail(story) == StoryDetail(
        id="S-0001",
        title="a title",
        state="backlog",
        description="why",
        given="a state",
        when="an action",
        then="another state",
        tasks=[TaskRow("T-0002", "a task title", "an output", "how", "backlog")],
    )
