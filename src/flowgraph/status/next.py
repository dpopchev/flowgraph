"""The lines that can start now: the next to start alone, or as many as the development allows.

Plain data read from the lines of the Backlog in the order of its queue, kept in one place for
every view that lists it. It follows `flowgraph.status.waits`, which sets what each line waits
for. The limit is a sum type mapped from the configuration here, since `flowgraph.development`
imports this package and may not be imported by it.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import assert_never

from flowgraph.feature import FeatureRow
from flowgraph.record import Parallel, Unlimited
from flowgraph.record.layers import Development
from flowgraph.work_item import WorkItemRow

type Line = WorkItemRow | FeatureRow


@dataclass(frozen=True)
class NextOnly:
    """The development is off: the next to start is the one line marked."""


@dataclass(frozen=True)
class Within:
    """At most that many work items are started at once, those started counted."""

    most: int


@dataclass(frozen=True)
class NoLimit:
    """The development is on and limits nothing: every line that waits for nothing is marked."""


# How many lines status marks as able to start now.
type StartLimit = NextOnly | Within | NoLimit


def start_limit(development: Development) -> StartLimit:
    """The limit the development sets on the lines marked: off, within a number, or none."""
    if not development.enabled:
        return NextOnly()
    match development.parallel:
        case Unlimited():
            return NoLimit()
        case Parallel(most):
            return Within(most)
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


def with_start_now(lines: Sequence[Line], limit: StartLimit, started: int) -> list[Line]:
    """The lines of the Backlog in their order, each one that can start now marked.

    Under a limit the places are those it leaves after the work items started; the first lines
    that can start take them. Off, the first line that can start is marked alone.
    """
    match limit:
        case NextOnly():
            return with_next(lines)
        case NoLimit():
            room = len(lines)
        case Within(most):
            room = max(most - started, 0)
        case _ as unreachable:
            assert_never(unreachable)
    marked: list[Line] = []
    for line in lines:
        takes = room > 0 and _can_start(line)
        room -= takes
        marked.append(replace(line, next_to_start=takes))
    return marked


def start_now_ids(rows: Iterable[Line]) -> list[str]:
    """The ids of the rows marked as able to start now, in the order given."""
    return [row.id for row in rows if row.next_to_start]
