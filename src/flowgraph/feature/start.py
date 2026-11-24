"""The start of a Feature, and what a Feature asks of the start of a work item under it.

A Feature is to its work items what a work item is to its Tasks: it starts with its first work
item and not without one, a work item of it does not start before it or while it is blocked, and
the work items of it started at once are limited by `development.parallel` alone. With the
development on it starts only once planned: each work item of it in Backlog holds a Task, and
a complexity too when an agent drives the development. Each
runs on the store of a record, as the commands of a work item do (`flowgraph.item.commands`).
"""

from collections.abc import Callable
from typing import assert_never

from flowgraph import work_item
from flowgraph.development import make_slug, slug_of_title
from flowgraph.development.driver import NO_COMPLEXITY, NoComplexityError, asks_complexity
from flowgraph.development.parallel import check_feature_parallel
from flowgraph.feature import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    FeatureRemovedError,
    RemovedFeature,
    StartedFeature,
    started_feature,
)
from flowgraph.item.commands import MESSAGE, ItemIdError, ToBranch, Written, parse_item_id
from flowgraph.parent import FeatureId, Standalone, feature_id_text, parse_feature_id
from flowgraph.record import Config, Now
from flowgraph.record.queue import queued
from flowgraph.record.store import Store
from flowgraph.relation.depends import check_first_waits
from flowgraph.status import backlog_as_added, rows_under
from flowgraph.task import BlockedError, CompletedAlreadyError, NoTaskError, TaskId
from flowgraph.work_item import (
    BlockedWorkItem,
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemId,
    WorkItemRow,
    WorkItemState,
    work_item_id_text,
)
from flowgraph.work_item.agent import make_agent
from flowgraph.work_item.handed import handed_work_item


class NoWorkItemError(ValueError):
    """A Feature started without a work item in Backlog to start with."""


class FeatureNotStartedError(ValueError):
    """A work item started before its Feature; names the Feature."""


def first_in_backlog(feature: FeatureId, store: Store) -> WorkItemId | None:
    """The work item the Feature starts next; None when it has none in Backlog.

    It is the first of its work items in Backlog in the order of the queue, so a Feature that
    holds completed work items starts with the one after them.
    """
    in_backlog = backlog_as_added(rows_under(feature, store))
    start_order = queued(store.load_queue(), in_backlog)
    return min(in_backlog, key=start_order.index, default=None)


def _first_lacking(
    feature: FeatureId, store: Store, lacks: Callable[[WorkItemRow], bool]
) -> WorkItemId | None:
    """The work item in Backlog of the Feature whose row lacks what `lacks` says, first in order.

    The order is the one of `first_in_backlog`: the queue over the order added.
    """
    rows = rows_under(feature, store)
    in_backlog = backlog_as_added(rows)
    start_order = queued(store.load_queue(), in_backlog)
    bare = [item for item in in_backlog if lacks(rows[item])]
    return min(bare, key=start_order.index, default=None)


def first_unplanned(feature: FeatureId, store: Store) -> WorkItemId | None:
    """The work item in Backlog of the Feature that holds no Task and starts first; else None."""
    return _first_lacking(feature, store, lambda row: not row.tasks)


def first_without_complexity(feature: FeatureId, store: Store) -> WorkItemId | None:
    """The work item in Backlog of the Feature with no complexity that starts first; else None."""
    return _first_lacking(feature, store, lambda row: not row.complexity)


def check_planned(feature: FeatureId, store: Store, *, complexity: bool) -> None:
    """Check that each work item in Backlog of the Feature is planned, and rated when asked.

    Raises NoTaskError, then NoComplexityError when `complexity` is true, naming the first
    such work item in start order.
    """
    named = feature_id_text(feature)
    unplanned = first_unplanned(feature, store)
    if unplanned is not None:
        raise NoTaskError(
            f"{named} cannot start: {work_item_id_text(unplanned)} has no Task to start with"
        )
    unrated = first_without_complexity(feature, store) if complexity else None
    if unrated is not None:
        unrated_named = work_item_id_text(unrated)
        raise NoComplexityError(f"{named} cannot start: {NO_COMPLEXITY.format(id=unrated_named)}")


def start_feature_item(
    feature: str,
    slug: str | None,
    store: Store,
    now: Now,
    config: Config,
    agent: str | None = None,
) -> Written:
    """Start the Feature of that id and its first work item with it; what the one write says.

    The work item names the branch to check out at the commit of the start: its slug is the one
    given, else the slug of its title; it is handed to the agent given, none by default, which
    raises AgentError when it is no agent. Raises FeatureIdError when the text is no Feature id,
    FeatureNotFoundError when the record holds no such Feature, StartedAlreadyError when it is
    started, CompletedAlreadyError when it is completed, RemovedAlreadyError when it is
    removed, NoWorkItemError when it has no work item in Backlog, StartWaitsError naming what its
    first work item still waits for, ParallelError when as many
    work items are started as the configuration starts at once, SlugError when the slug given
    is no slug, NoTaskError naming the Feature when its first work item has no Task or, with
    the development on, when a work item of it in Backlog has none, the first in start order named,
    and NoComplexityError naming the Feature and the first one in start order that holds no
    complexity when an agent drives the development; nothing is saved.
    """
    feature_id = parse_feature_id(feature)
    named = feature_id_text(feature_id)
    on = now()
    started = started_feature(store.features.load_feature(feature_id), on)
    first = first_in_backlog(feature_id, store)
    if first is None:
        raise NoWorkItemError(f"{named} has no work item in Backlog to start with")
    if config.development.enabled:
        check_planned(feature_id, store, complexity=asks_complexity(config))
    check_first_waits(named, first, store)
    check_feature_parallel(feature_id, store.find_work_item_rows, config)
    held = store.load_work_item(first)
    branch = make_slug(slug) if slug is not None else slug_of_title(held.title)
    handed = None if agent is None else make_agent(agent)
    try:
        begun = handed_work_item(work_item.started_work_item(held, on), handed)
    except NoTaskError as error:
        raise NoTaskError(f"{named} cannot start: {error}") from error
    store.features.save_feature(started)
    store.save_work_item(begun)
    out = f"started {named} with {work_item_id_text(first)}\n"
    return Written(out, MESSAGE.format(f"start {named}"), ToBranch(first, branch))


def _awaited_feature(item: WorkItemState) -> FeatureId | None:
    """The Feature a work item in Backlog is under; None for one standing alone or past Backlog."""
    match item:
        case WorkItem():
            match item.parent:
                case FeatureId():
                    return item.parent
                case Standalone():
                    return None
                case _ as unreachable:
                    assert_never(unreachable)
        case StartedWorkItem() | BlockedWorkItem() | CompletedWorkItem() | RemovedWorkItem():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def check_start_under_feature(item: str, store: Store) -> None:
    """Check that the start of the work item of that id is one its Feature takes.

    A started Feature takes the start of a work item beside those of it already started: only
    the configuration, what the work item depends on, its Task and its slug limit them. Raises
    FeatureNotStartedError naming the Feature when it is not started, BlockedError
    naming it and what it waits on when it is blocked, which starts no further work item,
    CompletedAlreadyError naming it when it is completed and RemovedAlreadyError naming it when
    it is removed. A work item standing alone passes, and so does one that is not in Backlog,
    which the start refuses; a Task, a Feature and a text that is no id are not read. Raises
    WorkItemNotFoundError when the record holds no such work item, as its start does.
    """
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    match item_id:
        case TaskId():
            return
        case WorkItemId():
            feature_id = _awaited_feature(store.load_work_item(item_id))
        case _ as unreachable:
            assert_never(unreachable)
    if feature_id is None:
        return
    named, feature = work_item_id_text(item_id), feature_id_text(feature_id)
    match store.features.load_feature(feature_id):
        case Feature():
            raise FeatureNotStartedError(
                f"{named} cannot start: {feature} is not started, start it first"
            )
        case StartedFeature():
            return
        case BlockedFeature(waiting_on=waiting_on):
            held = f"{feature} is blocked, waiting on {waiting_on}"
            raise BlockedError(f"{named} cannot start: {held}: unblock it first")
        case CompletedFeature():
            raise CompletedAlreadyError(f"{named} cannot start: {feature} is completed already")
        case RemovedFeature():
            raise FeatureRemovedError(feature_id, f"{named} cannot start: ")
        case _ as unreachable:
            assert_never(unreachable)
