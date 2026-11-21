"""Adding an Upkeep: it takes the next free Upkeep id and is saved whole, in Backlog."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError, make_scenario
from flowgraph.upkeep import (
    UPKEEP,
    UpkeepRow,
    UpkeepState,
    make_upkeep,
    make_upkeep_id,
)
from flowgraph.work_item import add_work_item

pytestmark = pytest.mark.command

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def add(saved: list[UpkeepState], then: str = "it still holds") -> object:
    """Add one Upkeep to a record whose highest Upkeep id is U-0002."""
    return add_work_item(
        kind=UPKEEP,
        title="a title",
        criterion=make_scenario("a behavior", "it runs", then),
        description="why",
        find_work_item_rows=lambda: [
            UpkeepRow("U-0002", "another", "backlog", created=NOW),
            UpkeepRow("U-0001", "one more", "backlog", created=NOW),
        ],
        save_work_item=saved.append,
        now=lambda: NOW,
    )


def test_it_returns_the_next_free_upkeep_id() -> None:
    assert add([]) == make_upkeep_id(3)


def test_it_saves_the_upkeep_whole_created_now() -> None:
    saved: list[UpkeepState] = []
    add(saved)
    scenario = make_scenario("a behavior", "it runs", "it still holds")
    assert saved == [make_upkeep(make_upkeep_id(3), "a title", scenario, "why", NOW)]


def test_a_blank_part_is_refused_by_name() -> None:
    with pytest.raises(EmptyPartError, match=r"^then is empty$"):
        add([], then=" ")
