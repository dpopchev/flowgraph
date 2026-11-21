"""Adding a Story: it takes the next free id of the record and is saved whole, in Backlog."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import STORY, StoryRow, StoryState, make_story, make_story_id
from flowgraph.work_item import add_work_item

pytestmark = pytest.mark.command

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TAKEN = [StoryRow("ST-0001", "an earlier title", "backlog")]


def add(saved: list[StoryState]) -> object:
    """Add one Story to a record that holds ST-0001, saving into the list."""
    return add_work_item(
        kind=STORY,
        title="a title",
        given="a state",
        when="an action",
        then="another state",
        description="",
        find_work_item_rows=lambda: TAKEN,
        save_work_item=saved.append,
        now=lambda: NOW,
    )


def test_it_returns_the_next_free_id() -> None:
    assert add([]) == make_story_id(2)


def test_it_saves_the_story_whole_created_now() -> None:
    saved: list[StoryState] = []
    add(saved)
    scenario = make_scenario("a state", "an action", "another state")
    assert saved == [make_story(make_story_id(2), "a title", scenario, "", NOW)]
