"""The Backlog queue: the placed items first, the rest as added, and one put before another.

It places the work items and the Features; a work item under a Feature among those of its Feature.
"""

import pytest

from flowgraph.parent import make_feature_id
from flowgraph.queue import (
    Entry,
    Inside,
    Line,
    NotInBacklogError,
    Placed,
    Queue,
    QueueError,
    SameItemError,
    UnderFeatureError,
    make_queue,
    moved_before,
    queued,
)
from flowgraph.work_item import make_kind, make_work_item_id

pytestmark = pytest.mark.model

CHORE = make_kind("Chore", "a", "CH")
ONE, TWO, THREE, FOUR, FIVE = (make_work_item_id(CHORE, number) for number in (1, 2, 3, 4, 5))
FEATURE, OTHER = make_feature_id(1), make_feature_id(2)
EMPTY = make_queue([])

# A Backlog of two work items standing alone and a Feature, two work items under it, and one
# under a Feature that has left the Backlog.
MIXED: list[Entry] = [
    Line(ONE),
    Line(FEATURE),
    Inside(TWO, FEATURE),
    Inside(THREE, FEATURE),
    Inside(FOUR, OTHER),
    Line(FIVE),
]
ALONE = "it is reordered among the work items of"


def lines(*placed: Placed) -> list[Entry]:
    """A Backlog of those items, each a line of it, in the order added."""
    return [Line(each) for each in placed]


def order_of(queue: Queue, among: list[Placed]) -> list[Placed]:
    """The order the queue gives those of MIXED, the others left out."""
    return [each for each in queued(queue, [entry.id for entry in MIXED]) if each in among]


def test_a_queue_placing_one_work_item_twice_is_refused() -> None:
    with pytest.raises(QueueError, match=r"^CH-0001 is placed twice$"):
        make_queue([ONE, TWO, ONE])


def test_a_queue_placing_one_feature_twice_is_refused() -> None:
    with pytest.raises(QueueError, match=r"^F-0001 is placed twice$"):
        make_queue([FEATURE, ONE, FEATURE])


def test_an_empty_queue_lists_the_backlog_as_added() -> None:
    assert queued(EMPTY, [ONE, TWO, THREE]) == [ONE, TWO, THREE]


def test_the_placed_items_are_listed_first_in_their_order() -> None:
    assert queued(make_queue([THREE, ONE]), [ONE, TWO, THREE]) == [THREE, ONE, TWO]


def test_a_placed_feature_is_listed_at_its_place_among_the_work_items() -> None:
    assert queued(make_queue([THREE, FEATURE]), [ONE, FEATURE, THREE]) == [THREE, FEATURE, ONE]


def test_the_items_never_placed_follow_as_added() -> None:
    assert queued(make_queue([THREE]), [ONE, TWO, THREE, FOUR]) == [THREE, ONE, TWO, FOUR]


def test_a_placed_item_no_longer_in_backlog_is_left_out() -> None:
    assert queued(make_queue([THREE, TWO]), [ONE, TWO]) == [TWO, ONE]


def test_an_item_is_put_right_before_an_earlier_one() -> None:
    assert moved_before(EMPTY, lines(ONE, TWO, THREE), THREE, TWO) == make_queue([ONE, THREE, TWO])


def test_an_item_is_put_right_before_a_later_one() -> None:
    assert moved_before(EMPTY, lines(ONE, TWO, THREE), ONE, THREE) == make_queue([TWO, ONE, THREE])


def test_a_move_starts_from_the_order_already_given() -> None:
    moved = moved_before(make_queue([THREE, ONE]), lines(ONE, TWO, THREE), TWO, THREE)
    assert moved == make_queue([TWO, THREE, ONE])


def test_a_move_places_only_the_items_still_in_backlog() -> None:
    moved = moved_before(make_queue([FOUR, ONE]), lines(ONE, TWO), TWO, ONE)
    assert moved == make_queue([TWO, ONE])


def test_a_feature_is_put_right_before_a_work_item_standing_alone() -> None:
    moved = moved_before(EMPTY, lines(ONE, TWO, FEATURE), FEATURE, TWO)
    assert moved == make_queue([ONE, FEATURE, TWO])


def test_a_work_item_standing_alone_is_put_right_before_a_feature() -> None:
    moved = moved_before(EMPTY, lines(ONE, FEATURE, TWO), TWO, FEATURE)
    assert moved == make_queue([ONE, TWO, FEATURE])


def test_a_work_item_under_a_feature_is_put_right_before_another_of_that_feature() -> None:
    assert moved_before(EMPTY, MIXED, THREE, TWO) == make_queue(
        [ONE, FEATURE, THREE, TWO, FOUR, FIVE]
    )


def test_a_move_of_a_line_of_the_backlog_keeps_the_order_inside_a_feature() -> None:
    placed = make_queue([THREE, ONE, TWO])
    assert order_of(moved_before(placed, MIXED, FIVE, ONE), [TWO, THREE]) == [THREE, TWO]


def test_a_move_inside_a_feature_keeps_the_order_of_the_lines_of_the_backlog() -> None:
    placed = make_queue([FIVE, TWO, FEATURE, THREE])
    moved = moved_before(placed, MIXED, THREE, TWO)
    assert order_of(moved, [ONE, FEATURE, FIVE]) == [FIVE, FEATURE, ONE]


def test_moving_an_item_not_in_backlog_is_refused() -> None:
    with pytest.raises(NotInBacklogError, match=r"^CH-0003 is not in Backlog$"):
        moved_before(EMPTY, lines(ONE, TWO), THREE, ONE)


def test_putting_an_item_before_one_not_in_backlog_is_refused() -> None:
    with pytest.raises(NotInBacklogError, match=r"^CH-0003 is not in Backlog$"):
        moved_before(EMPTY, lines(ONE, TWO), ONE, THREE)


def test_moving_a_feature_not_in_backlog_is_refused() -> None:
    with pytest.raises(NotInBacklogError, match=r"^F-0002 is not in Backlog$"):
        moved_before(EMPTY, MIXED, OTHER, ONE)


def test_putting_an_item_before_itself_is_refused() -> None:
    with pytest.raises(SameItemError, match=r"^CH-0001 cannot be put before itself$"):
        moved_before(EMPTY, lines(ONE, TWO), ONE, ONE)


def test_putting_a_feature_before_itself_is_refused() -> None:
    with pytest.raises(SameItemError, match=r"^F-0001 cannot be put before itself$"):
        moved_before(EMPTY, MIXED, FEATURE, FEATURE)


@pytest.mark.parametrize(
    ("item", "before", "named"),
    [
        (TWO, ONE, "CH-0002 is under F-0001"),
        (TWO, FEATURE, "CH-0002 is under F-0001"),
        (TWO, FOUR, "CH-0002 is under F-0001"),
        (ONE, TWO, "CH-0002 is under F-0001"),
        (FEATURE, FOUR, "CH-0004 is under F-0002"),
    ],
    ids=[
        "before-a-work-item-standing-alone",
        "before-its-feature",
        "before-a-work-item-of-another-feature",
        "a-work-item-standing-alone-before-it",
        "a-feature-before-it",
    ],
)
def test_a_work_item_under_a_feature_and_an_item_outside_it_are_refused_naming_the_feature(
    item: Placed, before: Placed, named: str
) -> None:
    feature = named.rpartition(" ")[2]
    with pytest.raises(UnderFeatureError, match=f"^{named}: {ALONE} {feature} alone$"):
        moved_before(EMPTY, MIXED, item, before)
