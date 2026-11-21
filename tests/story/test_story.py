"""A Story in Backlog: every part that must say something does, and it reads as a row."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.story import (
    StoryRow,
    make_scenario,
    make_story,
    make_story_id,
    story_row,
)

pytestmark = pytest.mark.model

SCENARIO = make_scenario("a state", "an action", "another state")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)


def test_a_blank_given_is_refused_by_name() -> None:
    with pytest.raises(EmptyPartError, match=r"^given is empty$"):
        make_scenario(" ", "an action", "another state")


@pytest.mark.parametrize(
    ("when", "then", "part"), [("", "another state", "when"), ("an action", "\n", "then")]
)
def test_a_blank_when_or_then_is_refused_by_name(when: str, then: str, part: str) -> None:
    with pytest.raises(EmptyPartError, match=f"^{part} is empty$"):
        make_scenario("a state", when, then)


def test_a_blank_title_is_refused_by_name() -> None:
    with pytest.raises(EmptyPartError, match=r"^title is empty$"):
        make_story(make_story_id(1), "", SCENARIO, "", CREATED)


def test_the_created_time_is_kept_to_the_second() -> None:
    story = make_story(make_story_id(1), "a title", SCENARIO, "", CREATED.replace(microsecond=7))
    assert story.created == CREATED


def test_a_story_reads_as_a_backlog_row() -> None:
    story = make_story(make_story_id(2), "a title", SCENARIO, "", CREATED)
    assert story_row(story) == StoryRow("ST-0002", "a title", "backlog")
