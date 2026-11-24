"""The criterion a work item realizes amended: in Backlog it is given, replaced or taken away.

An amend to another parent drops it unless one is given with it; a place for a work item that
stands alone is refused.
"""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.parent import (
    NO_CRITERION,
    STANDALONE,
    CriterionPlace,
    Parent,
    Realizes,
    RealizesError,
    make_feature_id,
)
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    Amendment,
    WorkItem,
    WorkItemState,
    amend_work_item,
    amended_work_item,
    append_task,
    make_kind,
    make_work_item,
    make_work_item_id,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
ABOVE, OTHER = make_feature_id(1), make_feature_id(2)
FIRST, SECOND = CriterionPlace(1), CriterionPlace(2)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
UNNAMED = append_task(make_work_item(ONE, "a title", SCENARIO, "", CREATED, ABOVE), TASK)
NAMED = append_task(
    make_work_item(ONE, "a title", SCENARIO, "", CREATED, ABOVE, realizes=SECOND), TASK
)
ALONE = append_task(make_work_item(ONE, "a title", SCENARIO, "", CREATED), TASK)

# The parent and the criterion an amend asks to be checked, as the check is asked.
type Asked = tuple[Parent, Realizes]


def never(*_: object) -> Never:
    """A check that an amend which names no criterion never asks."""
    raise AssertionError("an amend that names no criterion checks none")


def amended(item: WorkItem, amendment: Amendment) -> Realizes:
    """The criterion the item realizes once amended."""
    return amended_work_item(item, amendment).realizes


@pytest.mark.model
def test_an_amend_gives_a_work_item_under_a_feature_the_criterion() -> None:
    assert amended(UNNAMED, Amendment(realizes=SECOND)) == SECOND


@pytest.mark.model
def test_an_amend_replaces_the_criterion_it_had() -> None:
    assert amended(NAMED, Amendment(realizes=FIRST)) == FIRST


@pytest.mark.model
def test_an_amend_with_no_criterion_takes_it_away() -> None:
    assert amended(NAMED, Amendment(realizes=NO_CRITERION)) == NO_CRITERION


@pytest.mark.model
def test_an_amend_that_names_another_part_keeps_it() -> None:
    assert amended(NAMED, Amendment(title="one more")) == SECOND


@pytest.mark.model
def test_an_amend_to_another_parent_drops_it() -> None:
    assert amended(NAMED, Amendment(parent=OTHER)) == NO_CRITERION


@pytest.mark.model
def test_an_amend_to_another_parent_keeps_the_criterion_given_with_it() -> None:
    assert amended(NAMED, Amendment(parent=OTHER, realizes=FIRST)) == FIRST


@pytest.mark.model
def test_an_amend_to_the_parent_it_has_keeps_it() -> None:
    assert amended(NAMED, Amendment(parent=ABOVE)) == SECOND


@pytest.mark.model
def test_an_amend_to_no_parent_drops_it() -> None:
    assert amended(NAMED, Amendment(parent=STANDALONE)) == NO_CRITERION


@pytest.mark.model
def test_a_criterion_for_a_work_item_standing_alone_is_refused() -> None:
    with pytest.raises(RealizesError, match=r"this one stands alone$"):
        amended(ALONE, Amendment(realizes=SECOND))


@pytest.mark.model
def test_a_criterion_with_no_parent_is_refused() -> None:
    with pytest.raises(RealizesError, match=r"this one stands alone$"):
        amended(NAMED, Amendment(parent=STANDALONE, realizes=SECOND))


@pytest.mark.command
def test_the_criterion_is_checked_with_the_parent_and_the_place_when_one_is_named() -> None:
    asked: list[Asked] = []
    amend_work_item(
        item_id=ONE,
        amendment=Amendment(realizes=SECOND),
        load_work_item=lambda _: UNNAMED,
        save_work_item=lambda _: None,
        check_move=never,
        check_realizes=lambda *place: asked.append(place),
    )
    assert asked == [(ABOVE, SECOND)]


@pytest.mark.command
def test_no_criterion_is_checked_when_none_is_named() -> None:
    saved: list[WorkItemState] = []
    amend_work_item(
        item_id=ONE,
        amendment=Amendment(title="one more"),
        load_work_item=lambda _: NAMED,
        save_work_item=saved.append,
        check_move=never,
        check_realizes=never,
    )
    assert len(saved) == 1


@pytest.mark.command
def test_a_criterion_refused_by_the_check_saves_nothing() -> None:
    saved: list[WorkItemState] = []

    def refuse(*_: object) -> Never:
        raise RealizesError("F-0001 has no criterion 3: its criteria count from 1 to 2")

    with pytest.raises(RealizesError, match=r"has no criterion 3"):
        amend_work_item(
            item_id=ONE,
            amendment=Amendment(realizes=CriterionPlace(3)),
            load_work_item=lambda _: UNNAMED,
            save_work_item=saved.append,
            check_move=never,
            check_realizes=refuse,
        )
    assert saved == []
