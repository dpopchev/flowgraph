"""What a /goal line is refused for: hours, a driver, a Feature with nothing in Backlog."""

import pytest

from flowgraph.goal.model import (
    EmptyGoalError,
    GoalDriverError,
    GoalHoursError,
    check_driven_by_agent,
    check_scope,
    make_hours,
)
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.parent import parse_feature_id
from flowgraph.record.layers import UNGATED, Development, Driver, Merge, Unlimited

pytestmark = pytest.mark.model


def development(*, enabled: bool, driver: Driver) -> Development:
    return Development(
        enabled=enabled, parallel=Unlimited(), merge=Merge.MERGE_COMMIT, gate=UNGATED, driver=driver
    )


@pytest.mark.parametrize(("text", "hours"), [("1", 1), ("8", 8), ("24", 24)])
def test_hours_are_a_whole_number_of_1_or_more(text: str, hours: int) -> None:
    assert make_hours(text) == hours


@pytest.mark.parametrize("text", ["0", "-3", "2.5", "many", ""])
def test_hours_that_are_not_a_whole_number_of_1_or_more_are_refused_saying_so(text: str) -> None:
    with pytest.raises(GoalHoursError, match="a whole number of 1 or more"):
        make_hours(text)


def test_an_agent_driven_development_is_accepted() -> None:
    assert check_driven_by_agent(development(enabled=True, driver=Driver.AGENT)) is None


def test_a_development_off_is_refused_naming_development_enabled_and_how_to_set_it() -> None:
    with pytest.raises(GoalDriverError, match=r"fgraph config set development\.enabled true"):
        check_driven_by_agent(development(enabled=False, driver=Driver.AGENT))


def test_a_development_driven_by_a_developer_is_refused_naming_development_driver() -> None:
    with pytest.raises(GoalDriverError, match=r"fgraph config set development\.driver agent"):
        check_driven_by_agent(development(enabled=True, driver=Driver.DEVELOPER))


def test_a_development_off_is_refused_before_its_driver() -> None:
    with pytest.raises(GoalDriverError, match=r"development\.enabled"):
        check_driven_by_agent(development(enabled=False, driver=Driver.DEVELOPER))


def test_a_feature_with_no_work_item_is_refused_naming_it() -> None:
    with pytest.raises(EmptyGoalError, match="F-0002 holds no work item in Backlog"):
        check_scope(parse_feature_id("F-0002"), [])


def test_a_feature_with_a_work_item_is_accepted() -> None:
    item = parse_work_item_id_of_any_kind("S-0001")
    assert check_scope(parse_feature_id("F-0002"), [item]) is None
