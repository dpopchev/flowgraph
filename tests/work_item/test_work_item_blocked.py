"""The block of a started work item: the model, the moves it refuses and the commands that save."""

from dataclasses import fields, replace
from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_commit, make_scenario
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    NotBlockedError,
    NotStartedError,
    completed,
    make_task,
    make_task_id,
    removed,
    started,
)
from flowgraph.work_item import (
    Amendment,
    NotVerifiableError,
    RemovedAlreadyError,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
    amended_work_item,
    append_task,
    block_of,
    block_work_item,
    blocked_task,
    blocked_work_item,
    completed_task,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    noted_work_item,
    removed_work_item,
    started_task,
    started_work_item,
    still_open,
    unblock_work_item,
    unblocked_task,
    unblocked_work_item,
    verified_work_item,
    work_item_row,
)
from flowgraph.work_item.agent import Agent
from flowgraph.work_item.handed import handed_over, handed_work_item
from flowgraph.work_item.primitives import item_primitives

CHORE = make_kind("Chore", "a", "CH")
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 3, 10, 15, 20, 500, tzinfo=UTC)
ID = make_work_item_id(CHORE, 1)
FIRST, SECOND = make_task_id(1), make_task_id(2)
TASK = make_task(FIRST, "a task title", "an output", "", CREATED)
OTHER = make_task(SECOND, "another task", "an output", "", CREATED)
BACKLOG: WorkItem = append_task(
    append_task(make_work_item(ID, "a title", make_scenario("a", "b", "c"), "", CREATED), TASK),
    OTHER,
)
AGENT = Agent("sonnet-a1")
STARTED = started_task(handed_work_item(started_work_item(BACKLOG, ON), AGENT), FIRST, ON)
BLOCKED = blocked_work_item(STARTED, "no key", "developer", LATER)
DONE = completed(started(TASK, ON), ON, make_commit("abc1234"))
COMPLETED = completed_work_item(replace(STARTED, tasks=(DONE,)), ON, make_commit("abc1234"))
REMOVED = removed_work_item(BACKLOG, "filed by mistake", ON)
HELD = "CH-0001 is blocked, waiting on developer: unblock it first"


@pytest.mark.model
def test_a_blocked_work_item_holds_its_block_kept_to_the_second() -> None:
    assert (BLOCKED.reason, BLOCKED.since, BLOCKED.waiting_on) == (
        "no key",
        LATER.replace(microsecond=0),
        "developer",
    )


@pytest.mark.model
def test_a_blocked_work_item_holds_what_the_started_one_held() -> None:
    names = [each.name for each in fields(StartedWorkItem)]
    assert [getattr(BLOCKED, name) for name in names] == [getattr(STARTED, name) for name in names]


@pytest.mark.model
@pytest.mark.parametrize(
    ("item", "refusal", "error"),
    [
        (BACKLOG, NotStartedError, r"^CH-0001 is in Backlog: start it first$"),
        (BLOCKED, BlockedError, r"^CH-0001 is blocked already$"),
        (COMPLETED, CompletedAlreadyError, r"^CH-0001 is completed already$"),
        (REMOVED, RemovedAlreadyError, r"^CH-0001 is removed already$"),
    ],
    ids=["backlog", "blocked", "completed", "removed"],
)
def test_a_work_item_that_is_not_started_is_not_blocked(
    item: WorkItemState, refusal: type[Exception], error: str
) -> None:
    with pytest.raises(refusal, match=error):
        blocked_work_item(item, "no key", "developer", LATER)


@pytest.mark.model
@pytest.mark.parametrize(
    ("reason", "waiting_on", "error"),
    [(" ", "developer", r"^reason is empty$"), ("no key", "", r"^waiting on is empty$")],
    ids=["blank-reason", "blank-waiting-on"],
)
def test_a_block_with_a_blank_part_is_refused_naming_it(
    reason: str, waiting_on: str, error: str
) -> None:
    with pytest.raises(EmptyPartError, match=error):
        blocked_work_item(STARTED, reason, waiting_on, LATER)


@pytest.mark.model
def test_the_unblock_gives_back_the_started_work_item_it_was() -> None:
    assert unblocked_work_item(BLOCKED) == STARTED


@pytest.mark.model
@pytest.mark.parametrize(
    "item",
    [BACKLOG, STARTED, COMPLETED, REMOVED],
    ids=["backlog", "started", "completed", "removed"],
)
def test_a_work_item_that_is_not_blocked_is_not_unblocked(item: WorkItemState) -> None:
    with pytest.raises(NotBlockedError, match=r"^CH-0001 is not blocked$"):
        unblocked_work_item(item)


@pytest.mark.model
def test_the_block_of_a_blocked_work_item_is_its_reason_and_what_it_waits_on() -> None:
    assert block_of(BLOCKED) == ("no key", "developer")


@pytest.mark.model
def test_the_block_of_a_started_work_item_is_empty() -> None:
    assert block_of(STARTED) == ("", "")


@pytest.mark.model
def test_a_blocked_work_item_is_not_started() -> None:
    with pytest.raises(BlockedError, match=r"^CH-0001 is blocked: unblock it first$"):
        started_work_item(BLOCKED, LATER)


@pytest.mark.model
def test_a_blocked_work_item_is_not_completed() -> None:
    with pytest.raises(BlockedError, match=r"^CH-0001 is blocked: unblock it first$"):
        completed_work_item(BLOCKED, LATER, make_commit("abc1234"))


@pytest.mark.model
def test_a_blocked_work_item_is_not_verified() -> None:
    with pytest.raises(NotVerifiableError, match=r"^CH-0001 is blocked: fgraph verify takes "):
        verified_work_item(BLOCKED, "it ran", LATER)


@pytest.mark.model
def test_a_task_of_a_blocked_work_item_is_not_started() -> None:
    with pytest.raises(BlockedError, match=rf"^T-0002 cannot start: {HELD}$"):
        started_task(BLOCKED, SECOND, LATER)


@pytest.mark.model
def test_a_task_of_a_blocked_work_item_is_not_blocked() -> None:
    with pytest.raises(BlockedError, match=rf"^T-0001 cannot be blocked: {HELD}$"):
        blocked_task(BLOCKED, FIRST, "no review", "the reviewer", LATER)


@pytest.mark.model
def test_a_task_of_a_blocked_work_item_is_not_unblocked() -> None:
    with pytest.raises(BlockedError, match=rf"^T-0001 cannot be unblocked: {HELD}$"):
        unblocked_task(BLOCKED, FIRST)


@pytest.mark.model
def test_a_task_of_a_blocked_work_item_is_not_completed() -> None:
    with pytest.raises(BlockedError, match=rf"^T-0001 cannot complete: {HELD}$"):
        completed_task(BLOCKED, FIRST, LATER, make_commit("abc1234"))


@pytest.mark.model
def test_a_blocked_work_item_is_removed_with_its_open_tasks() -> None:
    assert removed_work_item(BLOCKED, "not wanted", LATER).tasks == tuple(
        removed(task, "not wanted", LATER) for task in BLOCKED.tasks
    )


@pytest.mark.model
def test_a_blocked_work_item_is_not_amended() -> None:
    with pytest.raises(BlockedError, match=r"^CH-0001 is blocked$"):
        amended_work_item(BLOCKED, Amendment(title="another title"))


@pytest.mark.model
def test_a_blocked_work_item_is_not_handed() -> None:
    with pytest.raises(BlockedError, match=r"^CH-0001 is blocked: unblock it first$"):
        handed_over(BLOCKED, Agent("opus-b2"))


@pytest.mark.model
def test_a_blocked_work_item_still_takes_a_task() -> None:
    task = make_task(make_task_id(3), "a third task", "an output", "", LATER)
    assert append_task(still_open(BLOCKED), task).tasks == (*BLOCKED.tasks, task)


@pytest.mark.model
def test_a_blocked_work_item_still_takes_a_line() -> None:
    line = make_knowledge_line(FINDING, "a text", LATER)
    assert noted_work_item(BLOCKED, line).knowledge == (line,)


@pytest.mark.model
def test_the_row_of_a_blocked_work_item_holds_its_state_its_started_time_and_its_agent() -> None:
    row = work_item_row(BLOCKED)
    assert (row.state, row.started, row.agent, row.reason, row.completed) == (
        "blocked",
        ON,
        "sonnet-a1",
        "",
        None,
    )


@pytest.mark.model
def test_a_blocked_work_item_holds_its_started_time_its_agent_and_its_block_as_primitives() -> None:
    held = item_primitives(BLOCKED)
    moves = ["started", "agent", "since", "reason", "waiting_on"]
    assert [(key, held[key]) for key in held if key in moves] == [
        ("started", ON),
        ("agent", "sonnet-a1"),
        ("since", LATER.replace(microsecond=0)),
        ("reason", "no key"),
        ("waiting_on", "developer"),
    ]


@pytest.mark.command
def test_block_work_item_saves_the_blocked_work_item() -> None:
    saved: list[WorkItemState] = []
    block_work_item(
        item_id=ID,
        reason="no key",
        waiting_on="developer",
        load_work_item=lambda _: STARTED,
        save_work_item=saved.append,
        now=lambda: LATER,
    )
    assert saved == [BLOCKED]


@pytest.mark.command
def test_a_refused_block_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(NotStartedError):
        block_work_item(
            item_id=ID,
            reason="no key",
            waiting_on="developer",
            load_work_item=lambda _: BACKLOG,
            save_work_item=saved.append,
            now=lambda: LATER,
        )
    assert saved == []


@pytest.mark.command
def test_unblock_work_item_saves_the_started_work_item() -> None:
    saved: list[WorkItemState] = []
    unblock_work_item(item_id=ID, load_work_item=lambda _: BLOCKED, save_work_item=saved.append)
    assert saved == [STARTED]


@pytest.mark.command
def test_a_refused_unblock_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(NotBlockedError):
        unblock_work_item(item_id=ID, load_work_item=lambda _: STARTED, save_work_item=saved.append)
    assert saved == []
