"""A work item that depends on another, as the commands ask of it: read from the record.

The relation is `flowgraph.relation`, which reads the record as plain data; this is its shell. It
reads that data from the store, checks the ids a command names before a write, gives the bucket of
each work item a view lists, and refuses the start of a work item that still waits.
"""

from collections.abc import Sequence
from dataclasses import replace

from flowgraph.item_id import ItemIdError, parse_item_id, parse_work_item_id_of_any_kind
from flowgraph.parent import NONE
from flowgraph.record.store import Store
from flowgraph.relation import (
    RelationError,
    Standing,
    Waited,
    amended_by,
    closes_cycle,
    filed_during_it,
    superseding,
    waiting_for,
)
from flowgraph.status import BACKLOG, COMPLETED, rows_by_id
from flowgraph.task import TaskId
from flowgraph.text import APART, BUCKETS
from flowgraph.work_item import (
    DependsRow,
    WorkItemDetail,
    WorkItemId,
    WorkItemNotFoundError,
    work_item_id_text,
)


class StartWaitsError(ValueError):
    """A work item started while one it depends on is not completed; names each with its bucket."""


def _bucket_of(state: str) -> str:
    """The bucket a work item in that state is listed in."""
    return next(name for name, states in BUCKETS if state in states)


def record_standing(store: Store) -> dict[str, Standing]:
    """Every work item of the record under its id as written, as the views of a relation read it."""
    return {
        row.id: Standing(
            _bucket_of(row.state),
            row.state == COMPLETED,
            tuple(row.depends_on),
            row.filed_during,
            row.superseded_by,
            row.amends,
        )
        for row in rows_by_id(store).values()
    }


def depends_asked(
    texts: Sequence[str] | None, item: str | None, store: Store
) -> tuple[WorkItemId, ...] | None:
    """The work items a command asks the item to depend on; None when it names none.

    `none` alone is none to depend on: an empty tuple. The item is the one amended, none for an
    add. Raises WorkItemIdError when a text is the id of no kind, WorkItemNotFoundError when the
    record holds no such work item and RelationError when `none` is given with others, when one
    is removed or when depending on it would close a cycle; nothing is written.
    """
    if texts is None:
        return None
    if NONE in texts:
        if len(texts) > 1:
            raise RelationError(f"{NONE} stands alone: it takes every dependency away")
        return ()
    asked = [parse_work_item_id_of_any_kind(text) for text in texts]
    record = record_standing(store)
    for each in asked:
        named = work_item_id_text(each)
        if named not in record:
            raise WorkItemNotFoundError(each)
        if record[named].bucket == APART:
            raise RelationError(f"a work item cannot depend on {named}: it is removed")
        if item is not None and closes_cycle(item, [named], record):
            raise RelationError(f"{item} cannot depend on {named}: it would close a cycle")
    return tuple(asked)


def filed_during_asked(text: str | None, store: Store) -> WorkItemId | None:
    """The work item a command asks the new one to be filed during; None when it names none.

    Raises WorkItemIdError when the text is the id of no kind, WorkItemNotFoundError when the
    record holds no such work item and RelationError when it is removed; nothing is written.
    """
    if text is None:
        return None
    asked = parse_work_item_id_of_any_kind(text)
    named = work_item_id_text(asked)
    record = record_standing(store)
    if named not in record:
        raise WorkItemNotFoundError(asked)
    if record[named].bucket == APART:
        raise RelationError(f"a work item cannot be filed during {named}: it is removed")
    return asked


def superseded_by_asked(text: str | None, item: str, store: Store) -> WorkItemId | None:
    """The work item a command asks the removed one to be superseded by; None when it names none.

    The item is the one removed. Raises WorkItemIdError when the text is the id of no kind,
    WorkItemNotFoundError when the record holds no such work item and RelationError when it is
    the item itself or is removed; nothing is written.
    """
    if text is None:
        return None
    asked = parse_work_item_id_of_any_kind(text)
    named = work_item_id_text(asked)
    record = record_standing(store)
    if named not in record:
        raise WorkItemNotFoundError(asked)
    if named == item:
        raise RelationError(f"{item} cannot be superseded by itself")
    if record[named].bucket == APART:
        raise RelationError(f"a work item cannot be superseded by {named}: it is removed")
    return asked


def amends_asked(text: str | None, store: Store) -> WorkItemId | None:
    """The completed work item a command asks the new one to amend; None when it names none.

    Raises WorkItemIdError when the text is the id of no kind, WorkItemNotFoundError when the
    record holds no such work item and RelationError when it is not completed; nothing is
    written.
    """
    if text is None:
        return None
    asked = parse_work_item_id_of_any_kind(text)
    named = work_item_id_text(asked)
    record = record_standing(store)
    if named not in record:
        raise WorkItemNotFoundError(asked)
    if not record[named].completed:
        raise RelationError(f"a work item cannot amend {named}: it is not completed")
    return asked


def bucketed(detail: WorkItemDetail, store: Store) -> WorkItemDetail:
    """The detail of a work item with the bucket each work item it depends on is listed in and
    the ids of the work items filed during it, of those it supersedes and of those that amend it,
    read from the record."""
    record = record_standing(store)
    return replace(
        detail,
        depends_on=[DependsRow(row.id, record[row.id].bucket) for row in detail.depends_on],
        filed_here=filed_during_it(detail.id, record),
        supersedes=superseding(detail.id, record),
        amended_by=amended_by(detail.id, record),
    )


def _listed(waited: Sequence[Waited]) -> str:
    """The work items a start waits for as a refusal lists them, each with its bucket."""
    return "; ".join(f"{each.id}, in {each.bucket}" for each in waited)


def _waited_for(item: WorkItemId, store: Store) -> str:
    """What the work item in Backlog of that id waits for, listed; empty when it waits for none.

    A work item that is not in Backlog waits for nothing: its start is refused for that.
    """
    named = work_item_id_text(item)
    record = record_standing(store)
    if named not in record or record[named].bucket != _bucket_of(BACKLOG):
        return ""
    return _listed(waiting_for(named, record))


def check_start_waits(item: str, store: Store) -> None:
    """Check that the start of the item of that id waits for no work item it depends on.

    Raises StartWaitsError naming each work item it depends on that is not completed, with its
    bucket. A Task, a text that is no id and a Feature, whose start checks its first work item,
    are not read.
    """
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    if isinstance(item_id, TaskId):
        return
    waited = _waited_for(item_id, store)
    if waited:
        raise StartWaitsError(f"{item} cannot start: it depends on {waited}")


def check_first_waits(feature: str, first: WorkItemId, store: Store) -> None:
    """Check that the start of the Feature, which starts its first work item, waits for nothing.

    Raises StartWaitsError naming the Feature and the first work item with what it waits for.
    """
    waited = _waited_for(first, store)
    if waited:
        named = work_item_id_text(first)
        held = f"its first work item {named} cannot start: it depends on {waited}"
        raise StartWaitsError(f"{feature} cannot start: {held}")
