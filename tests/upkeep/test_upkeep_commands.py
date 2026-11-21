"""The commands of an Upkeep: each loads it whole, writes or moves it, and saves it whole."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.task import CompletedAlreadyError, TaskNotFoundError, make_task, make_task_id
from flowgraph.upkeep import (
    UpkeepRow,
    UpkeepState,
    add_task,
    append_task,
    complete_task,
    complete_upkeep,
    completed_task,
    completed_upkeep,
    make_upkeep,
    make_upkeep_id,
    start_task,
    start_upkeep,
    started_task,
    started_upkeep,
)

pytestmark = pytest.mark.command

NOW = datetime(2026, 1, 3, tzinfo=UTC)
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
COMMIT = make_commit("abc1234")
BARE = make_upkeep(make_upkeep_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
TASK = make_task(make_task_id(4), "a task", "an output", "", CREATED)
UPKEEP = append_task(BARE, TASK)
BEGUN = started_task(started_upkeep(UPKEEP, CREATED), make_task_id(4), CREATED)


def test_a_task_written_for_an_upkeep_takes_the_next_task_id_of_the_record() -> None:
    saved: list[UpkeepState] = []
    add_task(
        parent="U-0001",
        title="a task",
        expected_output="an output",
        description="",
        load_upkeep=lambda _: BARE,
        find_task_ids=lambda: ["T-0003"],
        save_upkeep=saved.append,
        now=lambda: CREATED,
    )
    assert saved == [UPKEEP]


def test_a_task_written_for_a_completed_upkeep_is_refused() -> None:
    done = completed_upkeep(completed_task(BEGUN, make_task_id(4), NOW, COMMIT), NOW, COMMIT)
    with pytest.raises(CompletedAlreadyError, match=r"^U-0001 is completed already$"):
        add_task(
            parent="U-0001",
            title="a task",
            expected_output="an output",
            description="",
            load_upkeep=lambda _: done,
            find_task_ids=lambda: ["T-0004"],
            save_upkeep=[].append,
            now=lambda: NOW,
        )


def test_a_started_upkeep_is_saved_whole_started_now() -> None:
    saved: list[UpkeepState] = []
    start_upkeep(
        upkeep_id=make_upkeep_id(1),
        load_upkeep=lambda _: UPKEEP,
        save_upkeep=saved.append,
        now=lambda: NOW,
    )
    assert saved == [started_upkeep(UPKEEP, NOW)]


ROWS = [UpkeepRow("U-0001", "a title", "started")]


def test_a_started_task_returns_the_upkeep_that_holds_it() -> None:
    assert start_task(
        task_id=make_task_id(4),
        find_upkeep_rows=lambda: ROWS,
        load_upkeep=lambda _: started_upkeep(UPKEEP, CREATED),
        save_upkeep=[].append,
        now=lambda: NOW,
    ) == make_upkeep_id(1)


def test_a_task_no_upkeep_holds_is_refused_by_its_id() -> None:
    with pytest.raises(TaskNotFoundError, match=r"^no Task T-0009 in the record$"):
        complete_task(
            task_id=make_task_id(9),
            commit=COMMIT,
            find_upkeep_rows=lambda: ROWS,
            load_upkeep=lambda _: BEGUN,
            save_upkeep=[].append,
            now=lambda: NOW,
        )


def test_a_completed_upkeep_is_saved_whole_completed_now() -> None:
    half = completed_task(BEGUN, make_task_id(4), NOW, COMMIT)
    saved: list[UpkeepState] = []
    complete_upkeep(
        upkeep_id=make_upkeep_id(1),
        commit=COMMIT,
        load_upkeep=lambda _: half,
        save_upkeep=saved.append,
        now=lambda: NOW,
    )
    assert saved == [completed_upkeep(half, NOW, COMMIT)]
