"""Completing a Task and a Story: a started Task completes, a Story once every Task has."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import CommitError, make_commit, make_scenario
from flowgraph.story import (
    CompletedStory,
    append_task,
    completed_story,
    completed_task,
    make_story,
    make_story_id,
    started_story,
    started_task,
    still_open,
)
from flowgraph.task import (
    CompletedAlreadyError,
    CompletedTask,
    NotStartedError,
    OpenTaskError,
    TaskNotFoundError,
    make_task,
    make_task_id,
)

pytestmark = pytest.mark.model

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
DONE = datetime(2026, 1, 3, 17, 45, 10, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(1), "a task title", "an output", "how", CREATED)
STORY = append_task(make_story(make_story_id(1), "a title", SCENARIO, "why", CREATED), TASK)
BEGUN = started_task(started_story(STORY, ON), make_task_id(1), ON)
FINISHED = completed_task(BEGUN, make_task_id(1), DONE, COMMIT)
DONE_TASK = CompletedTask(
    id=make_task_id(1),
    title="a task title",
    expected_output="an output",
    description="how",
    created=CREATED,
    started=ON,
    completed=DONE.replace(microsecond=0),
    commit=COMMIT,
)


@pytest.mark.parametrize("text", ["abc1234", "0123456789abcdef0123456789abcdef01234567"])
def test_a_commit_is_7_to_40_hex_digits(text: str) -> None:
    assert make_commit(text).sha == text


@pytest.mark.parametrize(
    "text", ["xyz", "abc123", "ABC1234", "0123456789abcdef0123456789abcdef012345678"]
)
def test_a_text_that_is_no_commit_is_refused_by_itself(text: str) -> None:
    with pytest.raises(CommitError, match=f"^'{text}' is no commit: it is 7 to 40 hex digits$"):
        make_commit(text)


def test_a_started_task_completes_on_the_second_with_its_commit() -> None:
    assert FINISHED.tasks == (DONE_TASK,)


def test_a_task_in_backlog_under_a_started_story_is_refused_by_its_id() -> None:
    with pytest.raises(NotStartedError, match=r"^T-0001 is in Backlog: start it first$"):
        completed_task(started_story(STORY, ON), make_task_id(1), DONE, COMMIT)


def test_a_task_of_a_story_in_backlog_is_refused_by_its_id() -> None:
    with pytest.raises(NotStartedError, match=r"^T-0001 is in Backlog: start it first$"):
        completed_task(STORY, make_task_id(1), DONE, COMMIT)


def test_a_completed_task_is_refused_by_its_id() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^T-0001 is completed already$"):
        completed_task(FINISHED, make_task_id(1), DONE, COMMIT)


def test_a_task_the_story_does_not_hold_is_refused_by_its_id() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0002 in the record$"):
        completed_task(BEGUN, make_task_id(2), DONE, COMMIT)


def test_a_story_whose_tasks_are_completed_completes_on_the_second_with_its_commit() -> None:
    assert completed_story(FINISHED, DONE, make_commit("def5678")) == CompletedStory(
        id=make_story_id(1),
        title="a title",
        criterion=SCENARIO,
        description="why",
        created=CREATED,
        started=ON,
        completed=DONE.replace(microsecond=0),
        commit=make_commit("def5678"),
        tasks=(DONE_TASK,),
    )


def test_a_story_with_tasks_not_completed_is_refused_naming_them() -> None:
    second = make_task(make_task_id(2), "another task title", "another output", "", CREATED)
    begun = started_story(append_task(STORY, second), ON)
    with pytest.raises(
        OpenTaskError, match=r"^S-0001 has Tasks to complete first: T-0001, T-0002$"
    ):
        completed_story(begun, DONE, COMMIT)


def test_a_story_in_backlog_is_refused_by_its_id() -> None:
    with pytest.raises(NotStartedError, match=r"^S-0001 is in Backlog: start it first$"):
        completed_story(STORY, DONE, COMMIT)


def test_a_completed_story_is_refused_by_its_id() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^S-0001 is completed already$"):
        completed_story(completed_story(FINISHED, DONE, COMMIT), DONE, COMMIT)


def test_a_completed_story_does_not_start_again() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^S-0001 is completed already$"):
        started_story(completed_story(FINISHED, DONE, COMMIT), DONE)


def test_a_task_of_a_completed_story_does_not_start_again() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^T-0001 is completed already$"):
        started_task(completed_story(FINISHED, DONE, COMMIT), make_task_id(1), DONE)


def test_a_started_story_is_still_open() -> None:
    assert still_open(BEGUN) == BEGUN


def test_a_completed_story_is_open_no_more() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^S-0001 is completed already$"):
        still_open(completed_story(FINISHED, DONE, COMMIT))
