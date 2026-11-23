"""The /goal line of a Feature, worded from its ids, the limit and the hours; pure text."""

from collections.abc import Sequence
from typing import NewType, assert_never

from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.record.layers import Development, Driver, Limit, Parallel, Unlimited
from flowgraph.work_item import WorkItemId, work_item_id_text

Hours = NewType("Hours", int)

SET = "set it with: fgraph config set {key} {value}"


class GoalHoursError(ValueError):
    """Hours that are no whole number of 1 or more."""


class GoalDriverError(ValueError):
    """A goal asked of a record whose development is off or driven by a developer."""


class EmptyGoalError(ValueError):
    """A goal asked of a Feature with no work item in Backlog."""


def make_hours(text: str) -> Hours:
    """The hours of the bound, a whole number of 1 or more.

    Raises GoalHoursError for any other text.
    """
    if not (text.isascii() and text.isdigit() and int(text) >= 1):
        raise GoalHoursError(f"the hours are {text!r}: give a whole number of 1 or more")
    return Hours(int(text))


def check_driven_by_agent(development: Development) -> None:
    """Check that the development is on and driven by an agent.

    Raises GoalDriverError naming the key to set and how.
    """
    if not development.enabled:
        raise GoalDriverError(
            "development.enabled is off, and a goal is for a development driven by an agent: "
            + SET.format(key="development.enabled", value="true")
        )
    if development.driver is not Driver.AGENT:
        raise GoalDriverError(
            "development.driver is developer, and a goal is for one driven by an agent: "
            + SET.format(key="development.driver", value="agent")
        )


def check_scope(feature: FeatureId, items: Sequence[WorkItemId]) -> None:
    """Check that the Feature holds a work item to develop.

    Raises EmptyGoalError naming the Feature when items is empty.
    """
    if not items:
        raise EmptyGoalError(f"{feature_id_text(feature)} holds no work item in Backlog")


def _joined(ids: Sequence[str]) -> str:
    """The ids as a, a and b, or a, b and c."""
    *first, last = ids
    return f"{', '.join(first)} and {last}" if first else last


def _at_once(limit: Limit) -> str:
    """How many work items run at once under the limit."""
    match limit:
        case Parallel(most):
            return f"at most {most} at once as development.parallel says"
        case Unlimited():
            return "as many at once as can start, development.parallel setting no limit"
        case _:
            assert_never(limit)


def goal_line(feature: FeatureId, items: Sequence[WorkItemId], limit: Limit, hours: Hours) -> str:
    """The /goal line that develops the work items of the Feature in at most that many hours."""
    named = feature_id_text(feature)
    ids = _joined([work_item_id_text(each) for each in items])
    return (
        f"/goal Develop {named} until fgraph show {named} lists {ids} Completed, "
        f"or stop after {hours} hours. This session is the coordinator: it hands each whole "
        f"work item to one subagent, {_at_once(limit)}. The goal is met as well when this "
        "session prints [HALT] <id>: <the decision needed> on a change to a criterion, a Task "
        "or the scope of a work item, or a removal, that the developer has not agreed."
    )
