"""An item of any kind, named by its id: the store of a record, and the commands by id.

Each command reads the id, finds the kind it names and runs the work item command on the store;
it returns the line fgraph writes, or raises the refusal of the move.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import assert_never

from flowgraph import work_item
from flowgraph.criterion import make_commit
from flowgraph.queue import LoadQueue, SaveQueue, queued, read_queue, reorder, write_queue
from flowgraph.record import Now
from flowgraph.story import STORY
from flowgraph.task import TaskId, TaskIdError, parse_task_id, task_id_text
from flowgraph.text import show_text, status_text
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import (
    FindTaskIds,
    Kind,
    LoadWorkItem,
    SaveWorkItem,
    WorkItemDetail,
    WorkItemId,
    WorkItemIdError,
    WorkItemRow,
    parse_work_item_id,
    work_item_id_text,
)

# The kinds of work item a record holds, in the order fgraph reads them.
KINDS: tuple[Kind, ...] = (STORY, UPKEEP)

# The state of a row in Backlog, as the record writes it.
BACKLOG = "backlog"

# The rows of the work items of that kind in the record; an empty list when it holds none.
FindKindRows = Callable[[Kind], list[WorkItemRow]]

# The work item of that id as plain data; raises WorkItemNotFoundError when the record holds none.
FindWorkItemDetail = Callable[[WorkItemId], WorkItemDetail]

# The id of an item of any kind.
ItemId = WorkItemId | TaskId


@dataclass(frozen=True)
class Store:
    """The reads and writes of one record, each already bound to its directory."""

    find_work_item_rows: FindKindRows
    load_work_item: LoadWorkItem
    find_work_item_detail: FindWorkItemDetail
    find_task_ids: FindTaskIds
    save_work_item: SaveWorkItem
    load_queue: LoadQueue
    save_queue: SaveQueue


# The store of the record in that directory.
OpenStore = Callable[[Path], Store]


class ItemIdError(ValueError):
    """A text that is the id of no kind of item."""


def read_every_task_id(record: Path) -> list[str]:
    """Adapter: the ids of every Task of every kind in the record, as written, in no order."""
    return [task for kind in KINDS for task in work_item.read_task_ids(record, kind)]


def open_files(record: Path) -> Store:
    """The store of the record in that directory, kept as its files."""
    return Store(
        find_work_item_rows=partial(work_item.read_work_item_rows, record),
        load_work_item=partial(work_item.read_work_item, record),
        find_work_item_detail=partial(work_item.read_work_item_detail, record),
        find_task_ids=partial(read_every_task_id, record),
        save_work_item=partial(work_item.write_work_item, record),
        load_queue=partial(read_queue, record, KINDS),
        save_queue=partial(write_queue, record, KINDS),
    )


def kind_named(name: str) -> Kind:
    """The kind whose noun, in lower case, is the name; raises KeyError when none is."""
    named = {kind.noun.lower(): kind for kind in KINDS}
    return named[name]


def parse_work_item_id_of_any_kind(text: str) -> WorkItemId:
    """The id of a work item of any kind written as the text.

    Raises WorkItemIdError as the first kind does when the text is the id of none of them.
    """
    first, *others = KINDS
    for kind in others:
        try:
            return parse_work_item_id(kind, text)
        except WorkItemIdError:
            continue
    return parse_work_item_id(first, text)


def parse_item_id(text: str) -> ItemId:
    """The id of a work item of any kind, or of a Task, written as the text.

    Raises ItemIdError when the text is none of them.
    """
    parsers: list[Callable[[str], ItemId]] = [
        *(partial(parse_work_item_id, kind) for kind in KINDS),
        parse_task_id,
    ]
    for parse in parsers:
        try:
            return parse(text)
        except WorkItemIdError, TaskIdError:
            continue
    nouns = ", ".join(kind.noun for kind in KINDS)
    raise ItemIdError(f"{text!r} is no {nouns} or Task id")


def _rows_by_id(store: Store) -> dict[WorkItemId, WorkItemRow]:
    """The row of every work item in the record under its id, by kind and then by number."""
    return {
        parse_work_item_id(kind, row.id): row
        for kind in KINDS
        for row in store.find_work_item_rows(kind)
    }


def _backlog_as_added(rows: Mapping[WorkItemId, WorkItemRow]) -> list[WorkItemId]:
    """The work items in Backlog in the order added; those added at one time as the rows list."""
    backlog = [item_id for item_id, row in rows.items() if row.state == BACKLOG]
    return sorted(backlog, key=lambda item_id: rows[item_id].created)


def status_item(store: Store) -> str:
    """The text of the work items of every kind in the record, by bucket.

    The Backlog is listed in the order of its queue; the other buckets by kind and number.
    """
    rows = _rows_by_id(store)
    backlog = queued(store.load_queue(), _backlog_as_added(rows))
    moved_on = [row for row in rows.values() if row.state != BACKLOG]
    return status_text([*(rows[item_id] for item_id in backlog), *moved_on])


def reorder_item(item: str, before: str, store: Store) -> str:
    """Put the work item right before the other in the queue of the Backlog; the line saying so.

    Raises WorkItemIdError when a text is the id of no kind, NotInBacklogError when one of the
    two is not in Backlog and SameItemError when they are one work item; nothing is saved.
    """
    moved = parse_work_item_id_of_any_kind(item)
    other = parse_work_item_id_of_any_kind(before)
    reorder(
        item=moved,
        before=other,
        find_backlog=lambda: _backlog_as_added(_rows_by_id(store)),
        load_queue=store.load_queue,
        save_queue=store.save_queue,
    )
    return f"moved {work_item_id_text(moved)} before {work_item_id_text(other)}\n"


def show_item(item: str, store: Store) -> str:
    """The text of the work item of that id.

    Raises WorkItemIdError when the text is the id of no kind and WorkItemNotFoundError when the
    record holds no such item.
    """
    return show_text(store.find_work_item_detail(parse_work_item_id_of_any_kind(item)))


def add_item(
    kind: Kind,
    title: str,
    criterion: tuple[str, str, str],
    description: str,
    store: Store,
    now: Now,
) -> str:
    """Add a work item of that kind with its Given / When / Then; the line that says so.

    Raises EmptyPartError when the title or a part of the criterion is blank; nothing is saved.
    """
    given, when, then = criterion
    added = work_item.add_work_item(
        kind=kind,
        title=title,
        given=given,
        when=when,
        then=then,
        description=description,
        find_work_item_rows=partial(store.find_work_item_rows, kind),
        save_work_item=store.save_work_item,
        now=now,
    )
    return f"added {work_item_id_text(added)}\n"


def write_task(
    parent: str, title: str, expected_output: str, description: str, store: Store, now: Now
) -> str:
    """Write a Task for the work item named as parent; the line that says so.

    Its id is the next free one across every kind. Raises WorkItemIdError when the parent is the
    id of no kind, WorkItemNotFoundError when the record holds no such item,
    CompletedAlreadyError when it is completed and EmptyPartError when a part is blank; nothing
    is saved.
    """
    written = work_item.add_task(
        parent=parse_work_item_id_of_any_kind(parent),
        title=title,
        expected_output=expected_output,
        description=description,
        load_work_item=store.load_work_item,
        find_task_ids=store.find_task_ids,
        save_work_item=store.save_work_item,
        now=now,
    )
    return f"added {task_id_text(written)} to {parent}\n"


def _load_holder(store: Store) -> work_item.LoadHolder:
    """The load of the work item that holds a Task, among the items of every kind."""

    def holder(task_id: TaskId) -> work_item.WorkItemState:
        ids = [
            parse_work_item_id(kind, row.id)
            for kind in KINDS
            for row in store.find_work_item_rows(kind)
        ]
        return work_item.holder_of(task_id, ids, store.load_work_item)

    return holder


def start_item(item: str, store: Store, now: Now) -> str:
    """Start the work item or the Task of that id; the line that says so.

    Raises ItemIdError when the text is no id, or the refusal of the start; nothing is saved.
    """
    match parse_item_id(item):
        case WorkItemId() as item_id:
            work_item.start_work_item(
                item_id=item_id,
                load_work_item=store.load_work_item,
                save_work_item=store.save_work_item,
                now=now,
            )
            return f"started {work_item_id_text(item_id)}\n"
        case TaskId() as task_id:
            holder = work_item.start_task(
                task_id=task_id,
                load_holder=_load_holder(store),
                save_work_item=store.save_work_item,
                now=now,
            )
            return f"started {task_id_text(task_id)} of {work_item_id_text(holder)}\n"
        case _ as unreachable:
            assert_never(unreachable)


def complete_item(item: str, sha: str, store: Store, now: Now) -> str:
    """Complete the work item or the Task of that id in that commit; the line that says so.

    Raises ItemIdError when the text is no id, CommitError when the sha is no commit, or the
    refusal of the complete; nothing is saved.
    """
    match parse_item_id(item):
        case WorkItemId() as item_id:
            commit = make_commit(sha)
            work_item.complete_work_item(
                item_id=item_id,
                commit=commit,
                load_work_item=store.load_work_item,
                save_work_item=store.save_work_item,
                now=now,
            )
            return f"completed {work_item_id_text(item_id)} at {commit.sha}\n"
        case TaskId() as task_id:
            commit = make_commit(sha)
            holder = work_item.complete_task(
                task_id=task_id,
                commit=commit,
                load_holder=_load_holder(store),
                save_work_item=store.save_work_item,
                now=now,
            )
            task = task_id_text(task_id)
            return f"completed {task} of {work_item_id_text(holder)} at {commit.sha}\n"
        case _ as unreachable:
            assert_never(unreachable)
