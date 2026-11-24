"""The moves of a work item of any kind: it starts with a Task and completes once every Task has."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit, make_scenario
from flowgraph.task import (
    CompletedAlreadyError,
    ItemInBacklogError,
    NoTaskError,
    NotStartedError,
    OpenTaskError,
    StartedAlreadyError,
    completed,
    make_task,
    make_task_id,
    removed,
    removed_among,
    started,
)
from flowgraph.work_item import (
    CompletedWorkItem,
    StartedWorkItem,
    WorkItemState,
    append_task,
    blocked_work_item,
    commit_sha,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    started_task,
    started_work_item,
    state_name,
    still_open,
)
from flowgraph.work_item.agent import make_agent

pytestmark = pytest.mark.model

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, 500, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, 500, tzinfo=UTC)
DONE = datetime(2026, 1, 3, 17, 45, 10, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
SCENARIO = make_scenario("a state", "an action", "another state")
BARE = make_work_item(make_work_item_id(CHORE, 1), "a title", SCENARIO, "why", CREATED)
TASK = make_task(make_task_id(1), "a task title", "an output", "how", CREATED)
ITEM = append_task(BARE, TASK)
BEGUN = started_work_item(ITEM, ON)
HELD = replace(BEGUN, agent=make_agent("sonnet-a1"))
HALF = started_task(BEGUN, make_task_id(1), ON)
FINISHED = completed_task(HALF, make_task_id(1), DONE, COMMIT)
WHOLE = completed_work_item(FINISHED, DONE, COMMIT)


def test_a_work_item_keeps_its_created_time_to_the_second() -> None:
    assert BARE.created == CREATED.replace(microsecond=0)


def test_a_work_item_without_a_title_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^title is empty$"):
        make_work_item(make_work_item_id(CHORE, 1), " ", SCENARIO, "", CREATED)


def test_a_work_item_with_a_task_starts_on_the_second_with_its_task_in_backlog() -> None:
    assert started_work_item(ITEM, ON) == StartedWorkItem(
        id=make_work_item_id(CHORE, 1),
        title="a title",
        criterion=SCENARIO,
        description="why",
        created=CREATED.replace(microsecond=0),
        started=ON.replace(microsecond=0),
        tasks=(TASK,),
    )


def test_a_work_item_without_a_task_is_refused_by_its_id() -> None:
    with pytest.raises(NoTaskError, match=r"^CH-0001 has no Task to start with$"):
        started_work_item(BARE, ON)


def test_a_started_work_item_is_refused_by_its_id() -> None:
    with pytest.raises(StartedAlreadyError, match=r"^CH-0001 is started already$"):
        started_work_item(BEGUN, ON)


def test_a_started_work_item_an_agent_holds_is_refused_naming_the_agent() -> None:
    with pytest.raises(
        StartedAlreadyError, match=r"^CH-0001 is started already: sonnet-a1 holds it$"
    ):
        started_work_item(HELD, ON)


def test_a_task_of_a_work_item_in_backlog_is_refused_naming_both() -> None:
    with pytest.raises(ItemInBacklogError, match=r"^T-0001 cannot start: CH-0001 is in Backlog$"):
        started_task(ITEM, make_task_id(1), ON)


def test_a_task_of_a_work_item_in_backlog_is_not_completed() -> None:
    with pytest.raises(NotStartedError, match=r"^T-0001 is in Backlog: start it first$"):
        completed_task(ITEM, make_task_id(1), DONE, COMMIT)


def test_a_work_item_with_every_task_completed_completes_in_its_commit() -> None:
    assert completed_work_item(FINISHED, DONE, COMMIT) == CompletedWorkItem(
        id=make_work_item_id(CHORE, 1),
        title="a title",
        criterion=SCENARIO,
        description="why",
        created=CREATED.replace(microsecond=0),
        started=ON.replace(microsecond=0),
        completed=DONE.replace(microsecond=0),
        commit=COMMIT,
        tasks=(completed(started(TASK, ON), DONE, COMMIT),),
    )


def test_a_work_item_whose_tasks_are_completed_or_removed_completes_holding_both() -> None:
    other = make_task(make_task_id(2), "another task", "another output", "", CREATED)
    begun = started_work_item(append_task(ITEM, other), ON)
    done = completed_task(started_task(begun, make_task_id(1), ON), make_task_id(1), DONE, COMMIT)
    gone = replace(done, tasks=removed_among(done.tasks, make_task_id(2), "a reason", DONE))
    assert completed_work_item(gone, DONE, COMMIT).tasks == (
        completed(started(TASK, ON), DONE, COMMIT),
        removed(other, "a reason", DONE),
    )


def test_a_work_item_in_backlog_is_not_completed() -> None:
    with pytest.raises(NotStartedError, match=r"^CH-0001 is in Backlog: start it first$"):
        completed_work_item(ITEM, DONE, COMMIT)


def test_a_work_item_with_a_task_not_completed_is_refused_naming_it() -> None:
    with pytest.raises(OpenTaskError, match=r"^CH-0001 has Tasks to complete first: T-0001$"):
        completed_work_item(HALF, DONE, COMMIT)


def test_a_completed_work_item_is_not_completed_again() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^CH-0001 is completed already$"):
        completed_work_item(WHOLE, DONE, COMMIT)


def test_a_completed_work_item_takes_no_task() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^CH-0001 is completed already$"):
        still_open(WHOLE)


@pytest.mark.parametrize(
    ("item", "name"),
    [
        (ITEM, "backlog"),
        (HALF, "started"),
        (blocked_work_item(HALF, "no key", "developer", DONE), "blocked"),
        (WHOLE, "completed"),
    ],
)
def test_a_work_item_names_its_state_as_the_record_writes_it(
    item: WorkItemState, name: str
) -> None:
    assert state_name(item) == name


def test_a_completed_work_item_names_its_commit() -> None:
    assert commit_sha(WHOLE) == "abc1234"
