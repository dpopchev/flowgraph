"""The work items started at once: the start `[development] parallel` of the configuration refuses.

With the development on and the key set, a work item is started only while fewer than that many
are started, of every kind, counted from the rows `fgraph status` lists under InProgress, those
under a Feature among them. The start of a Feature starts one work item, so it is refused as the
start of that one is. Left out, the key limits nothing, and neither does it with the development
off.
"""

from collections.abc import Iterable
from typing import assert_never

from flowgraph.config import DEVELOPMENT_PARALLEL, Config, Parallel, Unlimited
from flowgraph.item import BACKLOG, STARTED, ItemIdError, parse_item_id
from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.store import KINDS, FindKindRows
from flowgraph.task import TaskId
from flowgraph.work_item import WorkItemId, WorkItemRow, work_item_id_text


class ParallelError(Exception):
    """A work item started beside as many as the configuration starts at once; names each."""


def _most(config: Config) -> int | None:
    """The most work items the configuration starts at once; None when it limits nothing."""
    if not config.development.enabled:
        return None
    match config.development.parallel:
        case Unlimited():
            return None
        case Parallel(most):
            return most
        case _ as unreachable:
            assert_never(unreachable)


def _check_room(named: str, rows: Iterable[WorkItemRow], most: int) -> None:
    """Check that fewer than that many of the rows are started; named is what starts one more.

    Raises ParallelError naming it, the key, its number and every started work item.
    """
    started = [row.id for row in rows if row.state == STARTED]
    if len(started) < most:
        return
    limit = f"{DEVELOPMENT_PARALLEL} = {most}"
    raise ParallelError(f"{named} cannot start: {limit}, started already: {', '.join(started)}")


def check_parallel(item: str, find_work_item_rows: FindKindRows, config: Config) -> None:
    """Check that the start of the item of that id leaves no more started than parallel allows.

    Raises ParallelError naming the key, its number and every started work item when as many
    are started already. A Task is neither counted nor limited. A text that is no id and a work
    item that is not in Backlog are left to the start, which refuses them, and so is the id of a
    Feature, whose start checks it. The rows are read only with the development on and the key
    set.
    """
    most = _most(config)
    if most is None:
        return
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    match item_id:
        case TaskId():
            return
        case WorkItemId():
            named = work_item_id_text(item_id)
            rows = [row for kind in KINDS for row in find_work_item_rows(kind)]
            if any(row.id == named and row.state == BACKLOG for row in rows):
                _check_room(named, rows, most)
        case _ as unreachable:
            assert_never(unreachable)


def check_feature_parallel(
    feature: FeatureId, find_work_item_rows: FindKindRows, config: Config
) -> None:
    """Check that the start of the Feature, which starts one work item, leaves no more started.

    It is asked once the Feature is known to start. Raises ParallelError naming the Feature, the
    key, its number and every started work item when as many are started already. The rows are
    read only with the development on and the key set.
    """
    most = _most(config)
    if most is not None:
        rows = [row for kind in KINDS for row in find_work_item_rows(kind)]
        _check_room(feature_id_text(feature), rows, most)
