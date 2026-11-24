"""The rows of the work items of a record, read from its store, and those of them in Backlog.

The rows are read under their id by kind and then by number; the Backlog is in the order added.
"""

from collections.abc import Mapping

from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.record.store import KINDS, Store
from flowgraph.work_item import WorkItemId, WorkItemRow, parse_work_item_id

# The state of a row in Backlog, as the record writes it.
BACKLOG = "backlog"

# The state of a completed row, as the record writes it.
COMPLETED = "completed"


def rows_by_id(store: Store) -> dict[WorkItemId, WorkItemRow]:
    """The row of every work item in the record under its id, by kind and then by number."""
    return {
        parse_work_item_id(kind, row.id): row
        for kind in KINDS
        for row in store.find_work_item_rows(kind)
    }


def rows_under(feature: FeatureId, store: Store) -> dict[WorkItemId, WorkItemRow]:
    """The row of every work item under the Feature under its id, by kind and then by number."""
    named = feature_id_text(feature)
    return {item_id: row for item_id, row in rows_by_id(store).items() if row.parent == named}


def backlog_as_added(rows: Mapping[WorkItemId, WorkItemRow]) -> list[WorkItemId]:
    """The work items in Backlog in the order added; those added at one time as the rows list."""
    backlog = [item_id for item_id, row in rows.items() if row.state == BACKLOG]
    return sorted(backlog, key=lambda item_id: rows[item_id].created)
