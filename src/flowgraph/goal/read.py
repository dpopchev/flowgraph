"""The /goal line of a Feature, read from the record: the shell of the goal."""

from flowgraph.feature.start import check_planned
from flowgraph.goal.model import (
    check_driven_by_agent,
    check_scope,
    goal_line,
    make_hours,
)
from flowgraph.parent import parse_feature_id
from flowgraph.record.layers import Development
from flowgraph.record.queue import queued
from flowgraph.record.store import Store
from flowgraph.status import backlog_as_added, rows_under


def goal_output(feature: str, hours: str, store: Store, development: Development) -> str:
    """The /goal line of the Feature for the work items it holds in Backlog, and its newline.

    The work items are taken in the order the Feature starts them. Raises GoalDriverError when
    the development is off or driven by a developer, GoalHoursError for hours that are no whole
    number of 1 or more, FeatureIdError or FeatureNotFoundError for a Feature that is none, and
    EmptyGoalError when it holds no work item in Backlog; it raises NoTaskError or
    NoComplexityError, in the words of the start of the Feature, when a work item of it in
    Backlog holds no Task or no complexity, the first in start order named; nothing is written.
    """
    check_driven_by_agent(development)
    bound = make_hours(hours)
    feature_id = parse_feature_id(feature)
    store.features.load_feature(feature_id)
    in_backlog = backlog_as_added(rows_under(feature_id, store))
    start_order = queued(store.load_queue(), in_backlog)
    items = sorted(in_backlog, key=start_order.index)
    check_scope(feature_id, items)
    check_planned(feature_id, store, complexity=True)
    return goal_line(feature_id, items, development.parallel, bound) + "\n"
