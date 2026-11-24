"""The lines that can start now: the next to start alone, or as many as the development allows.

Plain data read from the work items of the started Features and the lines of the Backlog in
the order of its queue, kept in one place for every view that lists it. It follows
`flowgraph.status.waits`, which sets what each line waits for. The limit is a sum type mapped
from the configuration here, since `flowgraph.development` imports this package and may not
be imported by it. With the development driven by an agent, a work item is planned only once
it holds a complexity beside its Task; the limit carries the driver.
"""

from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass, replace
from typing import assert_never

from flowgraph.feature import FeatureRow
from flowgraph.record import Parallel, Unlimited
from flowgraph.record.layers import Development, Driver
from flowgraph.status.buckets import BACKLOG_BUCKET
from flowgraph.work_item import WorkItemRow

type Line = WorkItemRow | FeatureRow

# The state of a row in Backlog, as the record writes it.
BACKLOG = "backlog"


@dataclass(frozen=True)
class NextOnly:
    """The development is off: the next to start is the one line marked."""


@dataclass(frozen=True)
class Within:
    """At most that many work items are started at once, those started counted."""

    most: int
    driver: Driver = Driver.DEVELOPER


@dataclass(frozen=True)
class NoLimit:
    """The development is on and limits nothing: every line that waits for nothing is marked."""

    driver: Driver = Driver.DEVELOPER


# How many lines status marks as able to start now.
type StartLimit = NextOnly | Within | NoLimit

# The one value of the next to start alone, the default of a view.
NEXT_ONLY = NextOnly()


def start_limit(development: Development) -> StartLimit:
    """The limit the development sets on the lines marked: off, within a number, or none."""
    if not development.enabled:
        return NextOnly()
    match development.parallel:
        case Unlimited():
            return NoLimit(development.driver)
        case Parallel(most):
            return Within(most, development.driver)
        case _ as unreachable:
            assert_never(unreachable)


def _can_start(line: Line) -> bool:
    """True when the start of the line takes it: it waits for nothing and has a work item to start.

    A Feature starts its first work item in Backlog, so one holding none cannot start.
    """
    match line:
        case FeatureRow():
            return line.held > 0 and not line.waits_for
        case WorkItemRow():
            return not line.waits_for


def with_next(lines: Sequence[Line]) -> list[Line]:
    """The lines of the Backlog in their order, the first one that can start marked as the next.

    None is marked when no line can start.
    """
    first = next((at for at, line in enumerate(lines) if _can_start(line)), None)
    return [replace(line, next_to_start=at == first) for at, line in enumerate(lines)]


# A place taken: the index of a row, and that of its work item when it is one under a Feature.
type _Place = tuple[int, int | None]


def _in_backlog(row: Line) -> bool:
    """True when the row is a line of the Backlog."""
    match row:
        case FeatureRow():
            return row.bucket == BACKLOG_BUCKET
        case WorkItemRow():
            return row.state == BACKLOG
        case _ as unreachable:
            assert_never(unreachable)


def _asked(item: WorkItemRow, driver: Driver) -> bool:
    """True when the work item holds what the driver asks: nothing of a developer, a complexity."""
    match driver:
        case Driver.DEVELOPER:
            return True
        case Driver.AGENT:
            return bool(item.complexity)
        case _ as unreachable:
            assert_never(unreachable)


def _planned(line: Line, driver: Driver) -> bool:
    """True when the line is planned: a work item holds a Task and what the driver asks.

    A Feature's work items in Backlog each do.
    """
    match line:
        case WorkItemRow():
            return bool(line.tasks) and _asked(line, driver)
        case FeatureRow():
            return all(
                item.tasks and _asked(item, driver)
                for item in line.work_items
                if item.state == BACKLOG
            )
        case _ as unreachable:
            assert_never(unreachable)


def _startable_under(row: Line, driver: Driver) -> list[int]:
    """The places, in the order held, of the work items of a started Feature that can start.

    One in Backlog that waits for nothing and holds a Task and what the driver asks. A Feature
    not started, a blocked one included, and a work item standing alone give none.
    """
    match row:
        case FeatureRow(is_started=True):
            return [
                at
                for at, item in enumerate(row.work_items)
                if item.state == BACKLOG
                and not item.waits_for
                and item.tasks
                and _asked(item, driver)
            ]
        case FeatureRow() | WorkItemRow():
            return []
        case _ as unreachable:
            assert_never(unreachable)


def _marked(at: int, row: Line, places: Collection[_Place]) -> Line:
    """The row with its own mark and those of its work items set by the places taken."""
    match row:
        case FeatureRow():
            items = [
                replace(item, next_to_start=(at, under) in places)
                for under, item in enumerate(row.work_items)
            ]
            return replace(row, work_items=items, next_to_start=(at, None) in places)
        case WorkItemRow():
            return replace(row, next_to_start=(at, None) in places)
        case _ as unreachable:
            assert_never(unreachable)


def with_start_now(rows: Sequence[Line], limit: StartLimit, started: int) -> list[Line]:
    """The rows in their order, each place that can start now marked.

    Under a limit the places are those it leaves after the work items started. The first to take
    them are the work items in Backlog of the started Features, in the order the rows hold the
    Features, then the lines of the Backlog in their order; a line that waits or is not planned
    is skipped; planned asks a complexity of each work item when the driver is an agent. Off,
    the first line of the Backlog that can start is marked alone, planned or not.
    """
    match limit:
        case NextOnly():
            at_backlog = [at for at, row in enumerate(rows) if _in_backlog(row)]
            marked = dict(zip(at_backlog, with_next([rows[at] for at in at_backlog]), strict=True))
            return [marked.get(at, row) for at, row in enumerate(rows)]
        case NoLimit(driver):
            room = None
        case Within(most, driver):
            room = max(most - started, 0)
        case _ as unreachable:
            assert_never(unreachable)
    under: list[_Place] = [
        (at, item) for at, row in enumerate(rows) for item in _startable_under(row, driver)
    ]
    lines: list[_Place] = [
        (at, None)
        for at, row in enumerate(rows)
        if _in_backlog(row) and _can_start(row) and _planned(row, driver)
    ]
    places = [*under, *lines][:room]
    return [_marked(at, row, places) for at, row in enumerate(rows)]


def _own_ids(row: Line) -> list[str]:
    """The ids of the work items marked under the row, the Feature's own mark apart."""
    match row:
        case FeatureRow():
            return [item.id for item in row.work_items if item.next_to_start]
        case WorkItemRow():
            return []
        case _ as unreachable:
            assert_never(unreachable)


def start_now_ids(rows: Iterable[Line]) -> list[str]:
    """The ids of the places marked as able to start now, in the order they take them.

    The work items under the started Features first, then the lines of the Backlog.
    """
    listed = list(rows)
    return [
        *(id_ for row in listed for id_ in _own_ids(row)),
        *(row.id for row in listed if row.next_to_start),
    ]
