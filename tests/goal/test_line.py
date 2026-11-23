"""The /goal line of a Feature: its ids, its limit and its bound, worded as a coordinator's goal."""

import pytest

from flowgraph.goal.model import Hours, goal_line
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.parent import parse_feature_id
from flowgraph.record.layers import UNLIMITED, Limit, Parallel
from flowgraph.work_item import WorkItemId

pytestmark = pytest.mark.view

FEATURE = parse_feature_id("F-0001")
WHOLE = (
    "/goal Develop F-0001 until fgraph show F-0001 lists S-0001, S-0002 and S-0003 Completed, "
    "or stop after 8 hours. This session is the coordinator: it hands each whole work item to "
    "one subagent, at most 3 at once as development.parallel says. The goal is met as well when "
    "this session prints [HALT] <id>: <the decision needed> on a change to a criterion, a Task "
    "or the scope of a work item, or a removal, that the developer has not agreed."
)


def items(*ids: str) -> list[WorkItemId]:
    return [parse_work_item_id_of_any_kind(each) for each in ids]


THREE = Parallel(3)


def line(*ids: str, limit: Limit = THREE, hours: int = 8) -> str:
    return goal_line(FEATURE, items(*ids), limit, Hours(hours))


def test_the_line_of_three_work_items_with_parallel_3_and_8_hours_is_the_whole_line() -> None:
    assert line("S-0001", "S-0002", "S-0003") == WHOLE


def test_one_id_is_named_alone() -> None:
    assert "lists S-0001 Completed," in line("S-0001")


def test_two_ids_are_joined_with_and() -> None:
    assert "lists S-0001 and S-0002 Completed," in line("S-0001", "S-0002")


def test_three_ids_are_joined_with_a_comma_and_and() -> None:
    assert "lists S-0001, S-0002 and S-0003 Completed," in line("S-0001", "S-0002", "S-0003")


def test_parallel_says_at_most_that_many_at_once_as_development_parallel_says() -> None:
    assert "at most 2 at once as development.parallel says." in line("S-0001", limit=Parallel(2))


def test_unlimited_says_as_many_at_once_as_can_start() -> None:
    assert "as many at once as can start, development.parallel setting no limit." in line(
        "S-0001", limit=UNLIMITED
    )


def test_the_bound_says_or_stop_after_the_hours() -> None:
    assert ", or stop after 4 hours. " in line("S-0001", hours=4)
