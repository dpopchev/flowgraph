"""Completing a Story or a Task: the Story that holds it is loaded, completed and saved whole."""

from datetime import UTC, datetime

import pytest

from flowgraph.story import (
    CompletedAlreadyError,
    StoryRow,
    StoryState,
    TaskNotFoundError,
    add_task,
    append_task,
    complete_story,
    complete_task,
    completed_story,
    completed_task,
    make_commit,
    make_scenario,
    make_story,
    make_story_id,
    make_task,
    make_task_id,
    started_story,
    started_task,
    story_id_text,
)

pytestmark = pytest.mark.command

NOW = datetime(2026, 1, 3, tzinfo=UTC)
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a", "b", "c")


def begun(number: int) -> StoryState:
    """A started Story of that number, holding one started Task of that number."""
    bare = make_story(make_story_id(number), "a title", SCENARIO, "", CREATED)
    story = append_task(bare, make_task(make_task_id(number), "a task", "an output", "", CREATED))
    return started_task(started_story(story, CREATED), make_task_id(number), CREATED)


RECORD = {story_id_text(held.id): held for held in (begun(1), begun(2))}


def complete(task: int, saved: list[StoryState]) -> object:
    """Complete the Task of that number in a record of two started Stories, one Task each."""
    return complete_task(
        task_id=make_task_id(task),
        commit=COMMIT,
        find_story_rows=lambda: [StoryRow(key, "a title", "started") for key in RECORD],
        load_story=lambda story_id: RECORD[story_id_text(story_id)],
        save_story=saved.append,
        now=lambda: NOW,
    )


def test_a_completed_task_returns_the_id_of_the_story_that_holds_it() -> None:
    assert complete(2, []) == make_story_id(2)


def test_a_completed_task_saves_its_story_whole_with_the_task_completed_now() -> None:
    saved: list[StoryState] = []
    complete(2, saved)
    assert saved == [completed_task(RECORD["ST-0002"], make_task_id(2), NOW, COMMIT)]


def test_a_task_no_story_holds_is_refused_by_its_id() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0003 in the record$"):
        complete(3, [])


HALF = completed_task(begun(1), make_task_id(1), NOW, COMMIT)


def test_a_completed_story_is_saved_whole_completed_now() -> None:
    saved: list[StoryState] = []
    complete_story(
        story_id=make_story_id(1),
        commit=COMMIT,
        load_story=lambda _: HALF,
        save_story=saved.append,
        now=lambda: NOW,
    )
    assert saved == [completed_story(HALF, NOW, COMMIT)]


def test_a_task_written_for_a_completed_story_is_refused_by_its_id() -> None:
    saved: list[StoryState] = []
    with pytest.raises(CompletedAlreadyError, match=r"^ST-0001 is completed already$"):
        add_task(
            parent="ST-0001",
            title="a task title",
            expected_output="an output",
            description="",
            load_story=lambda _: completed_story(HALF, NOW, COMMIT),
            find_task_ids=lambda: ["T-0001"],
            save_story=saved.append,
            now=lambda: NOW,
        )
