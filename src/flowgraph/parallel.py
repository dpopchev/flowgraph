"""The work items started at once: the start `[development] parallel` of the configuration refuses.

With the development on and the key set, a work item is started only while fewer than that many
are started, of every kind, counted from the rows `fgraph status` lists under InProgress. Left
out, the key limits nothing, and neither does it with the development off.
"""

from typing import assert_never

from flowgraph.config import DEVELOPMENT_PARALLEL, Config, Parallel, Unlimited
from flowgraph.item import BACKLOG, STARTED, ItemIdError, parse_item_id
from flowgraph.store import KINDS, FindKindRows
from flowgraph.task import TaskId
from flowgraph.work_item import WorkItemId, work_item_id_text


class ParallelError(Exception):
    """A work item started beside as many as the configuration starts at once; names each."""


def check_parallel(item: str, find_work_item_rows: FindKindRows, config: Config) -> None:
    """Check that the start of the item of that id leaves no more started than parallel allows.

    Raises ParallelError naming the key, its number and every started work item when as many
    are started already. A Task is neither counted nor limited. A text that is no id and a work
    item that is not in Backlog are left to the start, which refuses them. The rows are read
    only with the development on and the key set.
    """
    if not config.development.enabled:
        return
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    match item_id, config.development.parallel:
        case (TaskId(), _) | (_, Unlimited()):
            return
        case WorkItemId(), Parallel(most):
            named = work_item_id_text(item_id)
            rows = [row for kind in KINDS for row in find_work_item_rows(kind)]
            if not any(row.id == named and row.state == BACKLOG for row in rows):
                return
            started = [row.id for row in rows if row.state == STARTED]
            if len(started) < most:
                return
            limit = f"{DEVELOPMENT_PARALLEL} = {most}"
            already = ", ".join(started)
            raise ParallelError(f"{named} cannot start: {limit}, started already: {already}")
        case _ as unreachable:
            assert_never(unreachable)
