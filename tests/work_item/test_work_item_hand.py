"""The hand of a started work item to another agent: the model and the command that saves it."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import (
    CompletedAlreadyError,
    NotStartedError,
    completed,
    make_task,
    make_task_id,
    started,
)
from flowgraph.work_item import (
    RemovedAlreadyError,
    WorkItem,
    WorkItemState,
    append_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    removed_work_item,
    started_work_item,
)
from flowgraph.work_item.agent import Agent
from flowgraph.work_item.handed import hand_work_item, handed_over, handed_work_item

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_work_item_id(CHORE, 1)
TASK = make_task(make_task_id(1), "a task title", "an output", "", CREATED)
BACKLOG: WorkItem = append_task(
    make_work_item(ID, "a title", make_scenario("a", "b", "c"), "", CREATED), TASK
)
FIRST = Agent("sonnet-a1")
SECOND = Agent("opus-b2")
UNHANDED = started_work_item(BACKLOG, ON)
HANDED = handed_work_item(UNHANDED, FIRST)
DONE = completed(started(TASK, ON), ON, make_commit("abc1234"))
COMPLETED = completed_work_item(replace(HANDED, tasks=(DONE,)), ON, make_commit("abc1234"))
REMOVED = removed_work_item(BACKLOG, "filed by mistake", ON)


@pytest.mark.model
def test_a_started_work_item_with_no_agent_is_handed_and_holds_it() -> None:
    assert handed_over(UNHANDED, SECOND).agent == SECOND


@pytest.mark.model
def test_a_started_work_item_with_an_agent_holds_the_one_it_is_handed_to_now() -> None:
    assert handed_over(HANDED, SECOND).agent == SECOND


@pytest.mark.model
def test_the_handed_work_item_is_the_started_one_but_for_its_agent() -> None:
    assert replace(handed_over(HANDED, SECOND), agent=FIRST) == HANDED


@pytest.mark.model
def test_a_work_item_in_backlog_is_refused_saying_its_start_names_the_agent() -> None:
    with pytest.raises(
        NotStartedError, match=r"^CH-0001 is in Backlog: its start names the agent with --agent$"
    ):
        handed_over(BACKLOG, SECOND)


@pytest.mark.model
def test_a_completed_work_item_is_refused() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^CH-0001 is completed already$"):
        handed_over(COMPLETED, SECOND)


@pytest.mark.model
def test_a_removed_work_item_is_refused() -> None:
    with pytest.raises(RemovedAlreadyError, match=r"^CH-0001 is removed already$"):
        handed_over(REMOVED, SECOND)


@pytest.mark.command
def test_hand_work_item_saves_the_handed_work_item() -> None:
    saved: list[WorkItemState] = []
    hand_work_item(
        item_id=ID, agent=SECOND, load_work_item=lambda _: HANDED, save_work_item=saved.append
    )
    assert saved == [handed_over(HANDED, SECOND)]


@pytest.mark.command
def test_a_refused_hand_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(NotStartedError):
        hand_work_item(
            item_id=ID, agent=SECOND, load_work_item=lambda _: BACKLOG, save_work_item=saved.append
        )
    assert saved == []
