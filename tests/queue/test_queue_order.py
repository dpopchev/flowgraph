"""The Backlog queue: the placed work items first, the rest as added, and one put before another."""

import pytest

from flowgraph.queue import (
    NotInBacklogError,
    QueueError,
    SameItemError,
    make_queue,
    moved_before,
    queued,
)
from flowgraph.work_item import make_kind, make_work_item_id

pytestmark = pytest.mark.model

CHORE = make_kind("Chore", "a", "CH")
ONE, TWO, THREE, FOUR = (make_work_item_id(CHORE, number) for number in (1, 2, 3, 4))
EMPTY = make_queue([])


def test_a_queue_placing_one_work_item_twice_is_refused() -> None:
    with pytest.raises(QueueError, match=r"^CH-0001 is placed twice$"):
        make_queue([ONE, TWO, ONE])


def test_an_empty_queue_lists_the_backlog_as_added() -> None:
    assert queued(EMPTY, [ONE, TWO, THREE]) == [ONE, TWO, THREE]


def test_the_placed_items_are_listed_first_in_their_order() -> None:
    assert queued(make_queue([THREE, ONE]), [ONE, TWO, THREE]) == [THREE, ONE, TWO]


def test_the_items_never_placed_follow_as_added() -> None:
    assert queued(make_queue([THREE]), [ONE, TWO, THREE, FOUR]) == [THREE, ONE, TWO, FOUR]


def test_a_placed_item_no_longer_in_backlog_is_left_out() -> None:
    assert queued(make_queue([THREE, TWO]), [ONE, TWO]) == [TWO, ONE]


def test_an_item_is_put_right_before_an_earlier_one() -> None:
    assert moved_before(EMPTY, [ONE, TWO, THREE], THREE, TWO) == make_queue([ONE, THREE, TWO])


def test_an_item_is_put_right_before_a_later_one() -> None:
    assert moved_before(EMPTY, [ONE, TWO, THREE], ONE, THREE) == make_queue([TWO, ONE, THREE])


def test_a_move_starts_from_the_order_already_given() -> None:
    assert moved_before(make_queue([THREE, ONE]), [ONE, TWO, THREE], TWO, THREE) == make_queue(
        [TWO, THREE, ONE]
    )


def test_a_move_places_only_the_items_still_in_backlog() -> None:
    assert moved_before(make_queue([FOUR, ONE]), [ONE, TWO], TWO, ONE) == make_queue([TWO, ONE])


def test_moving_an_item_not_in_backlog_is_refused() -> None:
    with pytest.raises(NotInBacklogError, match=r"^CH-0003 is not in Backlog$"):
        moved_before(EMPTY, [ONE, TWO], THREE, ONE)


def test_putting_an_item_before_one_not_in_backlog_is_refused() -> None:
    with pytest.raises(NotInBacklogError, match=r"^CH-0003 is not in Backlog$"):
        moved_before(EMPTY, [ONE, TWO], ONE, THREE)


def test_putting_an_item_before_itself_is_refused() -> None:
    with pytest.raises(SameItemError, match=r"^CH-0001 cannot be put before itself$"):
        moved_before(EMPTY, [ONE, TWO], ONE, ONE)
