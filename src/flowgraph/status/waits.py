"""What a work item in Backlog waits for: the ids it depends on that are not completed.

Plain data read from the rows of the record, kept in one place for every view that lists it.
"""

from collections.abc import Mapping
from dataclasses import replace

from flowgraph.work_item import WorkItemRow

# The state of a row in Backlog, as the record writes it.
_BACKLOG = "backlog"

# The state of a completed row, as the record writes it.
_COMPLETED = "completed"


def waits_for(row: WorkItemRow, rows: Mapping[str, WorkItemRow]) -> list[str]:
    """The ids the row depends on that are not completed, in the order written.

    Only a work item in Backlog waits: a started one has been let start. An id the rows do not
    hold waits for nothing, as the refusal of a start reads it.
    """
    if row.state != _BACKLOG:
        return []
    return [named for named in row.depends_on if named in rows and rows[named].state != _COMPLETED]


def with_waits[Key](rows: Mapping[Key, WorkItemRow]) -> dict[Key, WorkItemRow]:
    """The rows under their keys, each one in Backlog carrying the ids it waits for."""
    by_text = {row.id: row for row in rows.values()}
    return {key: replace(row, waits_for=waits_for(row, by_text)) for key, row in rows.items()}
