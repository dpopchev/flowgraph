"""The work items ready for review, and the Tasks that count in the progress of a work item.

A work item is ready for review when it is started and holds a Task that is not removed, every
such Task of it completed; a removed Task counts in no progress. Derived at each listing from the
Tasks of a row and kept in no field and no file, as the block of a Feature is.
"""

from collections.abc import Iterable
from typing import assert_never

from flowgraph.feature import FeatureRow
from flowgraph.task import TaskRow
from flowgraph.work_item import STARTED, WorkItemRow

type Line = WorkItemRow | FeatureRow

# The state of a completed Task, as the record writes it.
_COMPLETED = "completed"

# The state of a removed Task, as the record writes it.
_REMOVED = "removed"


def counted(row: WorkItemRow) -> list[TaskRow]:
    """The Tasks of the row that count in its progress: every one that is not removed."""
    return [task for task in row.tasks if task.state != _REMOVED]


def ready_for_review(row: WorkItemRow) -> bool:
    """True when the row is started, holds a Task not removed and each such Task is completed."""
    tasks = counted(row)
    return row.state == STARTED and bool(tasks) and all(task.state == _COMPLETED for task in tasks)


def review_ids(rows: Iterable[Line]) -> list[str]:
    """The ids of the rows ready for review in the order given; a Feature gives those it lists.

    The rows a Feature lists are its started work items, in their order.
    """
    return [id_ for row in rows for id_ in _ids_of(row)]


def _ids_of(row: Line) -> list[str]:
    """The ids ready for review in one row: its own, or those under a Feature."""
    match row:
        case FeatureRow():
            return [item.id for item in row.started if ready_for_review(item)]
        case WorkItemRow():
            return [row.id] if ready_for_review(row) else []
        case _ as unreachable:
            assert_never(unreachable)
