"""The next to start: the first line of the Backlog its start would take.

Plain data read from the lines of the Backlog in the order of its queue, kept in one place for
every view that lists it. It follows `flowgraph.status.waits`, which sets what each line waits for.
"""

from collections.abc import Sequence
from dataclasses import replace

from flowgraph.feature import FeatureRow
from flowgraph.work_item import WorkItemRow

type Line = WorkItemRow | FeatureRow


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
