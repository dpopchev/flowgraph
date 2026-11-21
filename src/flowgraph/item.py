"""An item of any kind, named by its id: the commands by id, run on the store of a record.

Each command reads the id, finds the kind it names and runs the work item command on the store;
a view returns the text fgraph writes, a write what it says and the message of its commit, and
each raises the refusal of the move.
"""

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from functools import partial
from typing import assert_never

from flowgraph import work_item
from flowgraph.branch import Slug, SlugError, make_slug, slug_of_title
from flowgraph.criterion import Criterion, DecisionError, make_commit
from flowgraph.feature import FeatureRow, feature_row
from flowgraph.parent import STANDALONE, Parent, feature_id_text, parse_feature_id
from flowgraph.queue import queued, reorder
from flowgraph.record import Now
from flowgraph.store import KINDS, Store
from flowgraph.task import TaskId, TaskIdError, parse_task_id, task_id_text
from flowgraph.text import show_text, status_text
from flowgraph.work_item import (
    Kind,
    WorkItemId,
    WorkItemIdError,
    WorkItemRow,
    parse_work_item_id,
    work_item_id_text,
)

# The state of a row in Backlog, as the record writes it.
BACKLOG = "backlog"

# The id of an item of any kind.
ItemId = WorkItemId | TaskId

# The message of the commit that holds a write, for what was written.
MESSAGE = "chore: {} in the record"


@dataclass(frozen=True)
class ToBranch:
    """The work item a start branches, and the slug of its branch."""

    item: WorkItemId
    slug: Slug


@dataclass(frozen=True)
class Written:
    """What a write of the record says, and the message of the commit that holds it.

    `branch` names the branch to check out at that commit: set by the start of a work item only.
    """

    out: str
    message: str
    branch: ToBranch | None = None


class ItemIdError(ValueError):
    """A text that is the id of no kind of item."""


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


def _feature_rows(store: Store, rows: Collection[WorkItemRow]) -> list[FeatureRow]:
    """The Features of the record by number, each with the bucket its work items derive."""
    held = sorted(
        (parse_feature_id(text) for text in store.features.find_feature_ids()),
        key=lambda feature_id: feature_id.number,
    )
    return [
        feature_row(
            store.features.load_feature(feature_id),
            [row.state for row in rows if row.parent == feature_id_text(feature_id)],
        )
        for feature_id in held
    ]


def status_item(store: Store) -> str:
    """The text of the Features of the record, then its work items of every kind by bucket.

    The Features are listed by number, each with its derived bucket. The Backlog is listed in
    the order of its queue; the other buckets by kind and number.
    """
    rows = _rows_by_id(store)
    backlog = queued(store.load_queue(), _backlog_as_added(rows))
    moved_on = [row for row in rows.values() if row.state != BACKLOG]
    listed = [*(rows[item_id] for item_id in backlog), *moved_on]
    return status_text(listed, _feature_rows(store, rows.values()))


def reorder_item(item: str, before: str, store: Store) -> Written:
    """Put the work item right before the other in the queue of the Backlog; what the write says.

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
    placed = f"{work_item_id_text(moved)} before {work_item_id_text(other)}"
    return Written(f"moved {placed}\n", MESSAGE.format(f"reorder {placed}"))


def show_item(item: str, store: Store) -> str:
    """The text of the work item of that id.

    Raises WorkItemIdError when the text is the id of no kind and WorkItemNotFoundError when the
    record holds no such item.
    """
    return show_text(store.find_work_item_detail(parse_work_item_id_of_any_kind(item)))


def add_item(
    kind: Kind,
    title: str,
    criterion: Criterion,
    description: str,
    store: Store,
    now: Now,
    parent: Parent = STANDALONE,
) -> Written:
    """Add a work item of that kind with its criterion; what the write says.

    It stands alone unless a Feature is given as its parent. Raises EmptyPartError when the
    title is blank and CriterionError when the criterion is not of the form the kind takes;
    nothing is saved.
    """
    added = work_item.add_work_item(
        kind=kind,
        title=title,
        criterion=criterion,
        description=description,
        find_work_item_rows=partial(store.find_work_item_rows, kind),
        save_work_item=store.save_work_item,
        now=now,
        parent=parent,
    )
    text = work_item_id_text(added)
    return Written(f"added {text}\n", MESSAGE.format(f"add {text}"))


def amend_item(item: str, parts: work_item.Amendment, store: Store) -> Written:
    """Rewrite the parts named of the work item in Backlog of that id; what the write says.

    Raises WorkItemIdError when the text is the id of no kind, or the refusal of the amend.
    """
    item_id = parse_work_item_id_of_any_kind(item)
    load, save = store.load_work_item, store.save_work_item
    work_item.amend_work_item(
        item_id=item_id, amendment=parts, load_work_item=load, save_work_item=save
    )
    text = work_item_id_text(item_id)
    return Written(f"amended {text}\n", MESSAGE.format(f"amend {text}"))


def remove_item(item: str, reason: str, store: Store, now: Now) -> Written:
    """Remove the work item in Backlog of that id for the reason given; what the write says.

    Raises WorkItemIdError when the text is the id of no kind, or the refusal of the remove.
    """
    item_id = parse_work_item_id_of_any_kind(item)
    load, save = store.load_work_item, store.save_work_item
    work_item.remove_work_item(
        item_id=item_id, reason=reason, load_work_item=load, save_work_item=save, now=now
    )
    text = work_item_id_text(item_id)
    return Written(f"removed {text}\n", MESSAGE.format(f"remove {text}"))


def write_task(
    parent: str, title: str, expected_output: str, description: str, store: Store, now: Now
) -> Written:
    """Write a Task for the work item named as parent; what the write says.

    Its id is the next free one across every kind. Raises WorkItemIdError when the parent is the
    id of no kind, WorkItemNotFoundError when the record holds no such item,
    CompletedAlreadyError when it is completed and EmptyPartError when a part is blank; nothing
    is saved.
    """
    holder = parse_work_item_id_of_any_kind(parent)
    written = work_item.add_task(
        parent=holder,
        title=title,
        expected_output=expected_output,
        description=description,
        load_work_item=store.load_work_item,
        find_task_ids=store.find_task_ids,
        save_work_item=store.save_work_item,
        now=now,
    )
    task = task_id_text(written)
    message = MESSAGE.format(f"add {task} of {work_item_id_text(holder)}")
    return Written(f"added {task} to {parent}\n", message)


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


def start_item(item: str, slug: str | None, store: Store, now: Now) -> Written:
    """Start the work item or the Task of that id; what the write says.

    A work item names the branch to check out at the commit of its start: its slug is the one
    given, else the slug of its title. Raises ItemIdError when the text is no id, SlugError when
    the slug is none or is given for a Task, or the refusal of the start; nothing is saved.
    """
    match parse_item_id(item):
        case WorkItemId() as item_id:
            title = store.load_work_item(item_id).title
            named = make_slug(slug) if slug is not None else slug_of_title(title)
            work_item.start_work_item(
                item_id=item_id,
                load_work_item=store.load_work_item,
                save_work_item=store.save_work_item,
                now=now,
            )
            text = work_item_id_text(item_id)
            message = MESSAGE.format(f"start {text}")
            return Written(f"started {text}\n", message, ToBranch(item_id, named))
        case TaskId() as task_id:
            if slug is not None:
                raise SlugError(f"--slug names the branch of a work item: {item} is a Task")
            holder = work_item.start_task(
                task_id=task_id,
                load_holder=_load_holder(store),
                save_work_item=store.save_work_item,
                now=now,
            )
            task = f"{task_id_text(task_id)} of {work_item_id_text(holder)}"
            return Written(f"started {task}\n", MESSAGE.format(f"start {task}"))
        case _ as unreachable:
            assert_never(unreachable)


def block_item(task: str, reason: str, waiting_on: str, store: Store, now: Now) -> Written:
    """Block the started Task of that id for the reason given; what the write says.

    Raises TaskIdError when the text is no Task id, or the refusal of the block; nothing is
    saved.
    """
    task_id = parse_task_id(task)
    holder = work_item.block_task(
        task_id=task_id,
        reason=reason,
        waiting_on=waiting_on,
        load_holder=_load_holder(store),
        save_work_item=store.save_work_item,
        now=now,
    )
    blocked = f"{task_id_text(task_id)} of {work_item_id_text(holder)}"
    return Written(f"blocked {blocked}\n", MESSAGE.format(f"block {blocked}"))


def unblock_item(task: str, store: Store) -> Written:
    """Unblock the blocked Task of that id; what the write says.

    Raises TaskIdError when the text is no Task id, or the refusal of the unblock; nothing is
    saved.
    """
    task_id = parse_task_id(task)
    holder = work_item.unblock_task(
        task_id=task_id, load_holder=_load_holder(store), save_work_item=store.save_work_item
    )
    unblocked = f"{task_id_text(task_id)} of {work_item_id_text(holder)}"
    return Written(f"unblocked {unblocked}\n", MESSAGE.format(f"unblock {unblocked}"))


def complete_item(
    item: str, sha: str, store: Store, now: Now, decision: str | None = None
) -> Written:
    """Complete the work item or the Task of that id in that commit; what the write says.

    A Spike is completed with the decision that answers its hypothesis. Raises ItemIdError when
    the text is no id, CommitError when the sha is no commit, DecisionError when a Spike has no
    decision or another item is given one, or the refusal of the complete; nothing is saved.
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
                decision=decision,
            )
            text = work_item_id_text(item_id)
            return Written(
                f"completed {text} at {commit.sha}\n", MESSAGE.format(f"complete {text}")
            )
        case TaskId() as task_id:
            if decision is not None:
                named = task_id_text(task_id)
                raise DecisionError(
                    f"{named} takes no decision: only a Spike is completed with one"
                )
            commit = make_commit(sha)
            holder = work_item.complete_task(
                task_id=task_id,
                commit=commit,
                load_holder=_load_holder(store),
                save_work_item=store.save_work_item,
                now=now,
            )
            task = f"{task_id_text(task_id)} of {work_item_id_text(holder)}"
            return Written(
                f"completed {task} at {commit.sha}\n", MESSAGE.format(f"complete {task}")
            )
        case _ as unreachable:
            assert_never(unreachable)
