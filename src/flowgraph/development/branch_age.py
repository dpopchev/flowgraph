"""The age of the branch of a started work item, said and never refused.

The smallest reading of S-0098: the age runs from the time the work item was started, which the
record holds, not from a commit of git.
"""

from dataclasses import replace
from datetime import datetime, timedelta
from typing import assert_never

from flowgraph.record import Now
from flowgraph.record.layers import BranchMax, Development, MaxDays, NoMax, age_text, branched
from flowgraph.record.store import FindKindRows, Store
from flowgraph.work_item import IN_PROGRESS, Kind, WorkItemRow


def older_than(started: datetime | None, branch_max: BranchMax, now: datetime) -> str:
    """The age as the key writes it when more than that many days passed since the start.

    Empty for no start, for no age and for a branch of that age or younger.
    """
    match branch_max:
        case MaxDays(days) if started is not None and now - started > timedelta(days=days):
            return age_text(branch_max) or ""
        case MaxDays() | NoMax():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def aged(store: Store, development: Development, now: Now) -> Store:
    """The store whose rows of a started or blocked work item say the age their branch passed.

    The store itself, the clock never read, with the development off, on the trunk and for a
    key that holds no age; the clock is read once per listing.
    """
    if not branched(development) or age_text(development.branch_max) is None:
        return store
    find: FindKindRows = store.find_work_item_rows

    def find_work_item_rows(kind: Kind) -> list[WorkItemRow]:
        rows = find(kind)
        at = now()
        return [
            replace(row, branch_older_than=older_than(row.started, development.branch_max, at))
            if row.state in IN_PROGRESS
            else row
            for row in rows
        ]

    return replace(store, find_work_item_rows=find_work_item_rows)
