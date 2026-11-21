"""A Task in Backlog: its title and expected output say something, and its Story holds it."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.story import (
    append_task,
    make_scenario,
    make_story,
    make_story_id,
    make_task,
    make_task_id,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
STORY = make_story(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
FIRST = make_task(make_task_id(1), "a task title", "an output", "", CREATED)
SECOND = make_task(make_task_id(2), "another task title", "another output", "", CREATED)


def test_a_blank_title_is_refused_by_name() -> None:
    with pytest.raises(EmptyPartError, match=r"^title is empty$"):
        make_task(make_task_id(1), " ", "an output", "", CREATED)


def test_a_blank_expected_output_is_refused_as_output() -> None:
    with pytest.raises(EmptyPartError, match=r"^output is empty$"):
        make_task(make_task_id(1), "a task title", "\n", "", CREATED)


def test_the_created_time_is_kept_to_the_second() -> None:
    late = CREATED.replace(microsecond=7)
    assert make_task(make_task_id(1), "a task title", "an output", "", late).created == CREATED


def test_a_story_holds_a_task_written_for_it_after_those_it_had() -> None:
    assert append_task(append_task(STORY, FIRST), SECOND).tasks == (FIRST, SECOND)
