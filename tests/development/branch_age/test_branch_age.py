"""The age of the branch of a started work item: said by the rows of the store, never refused."""

from datetime import UTC, datetime, timedelta
from typing import Never

import pytest

from flowgraph.development.branch_age import aged, older_than
from flowgraph.record import make_config
from flowgraph.record.layers import NO_MAX, Development, MaxDays
from flowgraph.record.store import Store
from flowgraph.story import STORY
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.command

STARTED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = STARTED + timedelta(days=2)
AGED = make_config('[development]\nenabled = true\nbranch_max = "1d"\n').development
TRUNK = make_config('[development]\nenabled = true\nmode = "trunk"\nbranch_max = "1d"\n')
OFF = make_config('[development]\nbranch_max = "1d"\n')
UNAGED = make_config("[development]\nenabled = true\n")
ROWS = [
    WorkItemRow("S-0001", "started", "started", created=STARTED, started=STARTED),
    WorkItemRow("S-0002", "blocked", "blocked", created=STARTED, started=STARTED),
    WorkItemRow("S-0003", "backlog", "backlog", created=STARTED),
    WorkItemRow("S-0004", "completed", "completed", "abc1234", created=STARTED, started=STARTED),
]


def never(*_: object) -> Never:
    """A read of the record or of the clock that the check never asks for."""
    raise AssertionError("the store or the clock is asked for what the check never asks")


def listing() -> Store:
    """A store whose rows are ROWS and whose every other callable is never."""
    return Store(
        find_work_item_rows=lambda kind: list(ROWS),
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def marks(store: Store) -> dict[str, str]:
    """The age each Story row of the store says, by id."""
    return {row.id: row.branch_older_than for row in store.find_work_item_rows(STORY)}


def test_two_days_past_the_start_is_older_than_one_day() -> None:
    assert older_than(STARTED, MaxDays(1), NOW) == "1d"


def test_one_day_past_the_start_is_not_older_than_one_day() -> None:
    assert older_than(STARTED, MaxDays(1), STARTED + timedelta(days=1)) == ""


def test_thirty_one_days_past_the_start_is_older_than_thirty_days() -> None:
    assert older_than(STARTED, MaxDays(30), STARTED + timedelta(days=31)) == "30d"


def test_a_work_item_with_no_start_is_not_older() -> None:
    assert older_than(None, MaxDays(1), NOW) == ""


def test_no_age_is_never_older() -> None:
    assert older_than(STARTED, NO_MAX, NOW) == ""


def test_a_started_row_two_days_old_is_marked() -> None:
    assert marks(aged(listing(), AGED, lambda: NOW))["S-0001"] == "1d"


def test_a_blocked_row_two_days_old_is_marked() -> None:
    assert marks(aged(listing(), AGED, lambda: NOW))["S-0002"] == "1d"


def test_a_row_in_backlog_is_left_unmarked() -> None:
    assert marks(aged(listing(), AGED, lambda: NOW))["S-0003"] == ""


def test_a_completed_row_is_left_unmarked() -> None:
    assert marks(aged(listing(), AGED, lambda: NOW))["S-0004"] == ""


@pytest.mark.parametrize(
    "development",
    [OFF.development, TRUNK.development, UNAGED.development],
    ids=["the-development-off", "the-trunk", "no-age"],
)
def test_the_store_is_returned_as_given_and_the_clock_never_read(
    development: Development,
) -> None:
    store = listing()
    assert aged(store, development, never) is store
