"""The reorder command: it loads the queue whole, puts one item before another, saves it."""

import pytest

from flowgraph.parent import make_feature_id
from flowgraph.queue import Line, NotInBacklogError, Queue, make_queue, reorder
from flowgraph.work_item import make_kind, make_work_item_id

pytestmark = pytest.mark.command

CHORE = make_kind("Chore", "a", "CH")
ONE, TWO, THREE = (make_work_item_id(CHORE, number) for number in (1, 2, 3))
FEATURE = make_feature_id(1)


def test_a_reorder_saves_the_queue_with_the_item_before_the_other() -> None:
    saved: list[Queue] = []
    reorder(
        item=THREE,
        before=ONE,
        find_backlog=lambda: [Line(ONE), Line(TWO), Line(THREE)],
        load_queue=lambda: make_queue([TWO]),
        save_queue=saved.append,
    )
    assert saved == [make_queue([TWO, THREE, ONE])]


def test_a_reorder_saves_the_queue_with_a_feature_before_a_work_item() -> None:
    saved: list[Queue] = []
    reorder(
        item=FEATURE,
        before=ONE,
        find_backlog=lambda: [Line(ONE), Line(TWO), Line(FEATURE)],
        load_queue=lambda: make_queue([TWO]),
        save_queue=saved.append,
    )
    assert saved == [make_queue([TWO, FEATURE, ONE])]


def test_a_reorder_refused_saves_nothing() -> None:
    saved: list[Queue] = []
    with pytest.raises(NotInBacklogError):
        reorder(
            item=THREE,
            before=ONE,
            find_backlog=lambda: [Line(ONE), Line(TWO)],
            load_queue=lambda: make_queue([]),
            save_queue=saved.append,
        )
    assert saved == []
