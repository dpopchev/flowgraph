"""An item of any kind, named by its id: the commands by id, run on the store of a record.

Each command reads the id, finds the kind it names and runs the work item command on the store;
a view returns the text fgraph writes, a write what it says and the message of its commit, and
each raises the refusal of the move. The moves of an item by its id are in flowgraph.item.moves.
"""

from dataclasses import dataclass
from functools import partial

from flowgraph import work_item
from flowgraph.criterion import Criterion
from flowgraph.development import Slug
from flowgraph.feature.move import check_move
from flowgraph.item.id import (
    ItemId,
    ItemIdError,
    kind_named,
    parse_amended_id,
    parse_item_id,
    parse_placed_id,
    parse_work_item_id_of_any_kind,
)
from flowgraph.parent import STANDALONE, FeatureId, Parent
from flowgraph.record import Now
from flowgraph.record.queue import placed_text, reorder
from flowgraph.record.store import Store
from flowgraph.relation.depends import bucketed
from flowgraph.status import BACKLOG, COMPLETED, STARTED, find_backlog, show_text, status_item
from flowgraph.task import task_id_text
from flowgraph.work_item import Kind, WorkItemId, work_item_id_text

# The ids of an item live in id.py and the listing of the status in flowgraph.status; both stay
# importable from here.
__all__ = [
    "BACKLOG",
    "COMPLETED",
    "STARTED",
    "ItemId",
    "ItemIdError",
    "kind_named",
    "parse_item_id",
    "parse_work_item_id_of_any_kind",
    "status_item",
]

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
    `completes` names the Feature the write completes: set by the completion of the last work
    item of a started Feature only, which a landing tags main at under `delivery.tag`.
    """

    out: str
    message: str
    branch: ToBranch | None = None
    completes: FeatureId | None = None


def reorder_item(item: str, before: str, store: Store) -> Written:
    """Put the work item or the Feature right before the other in the queue of the Backlog.

    Returns what the write says. Raises ItemIdError when a text is the id of neither,
    NotInBacklogError when one of the two is not in Backlog, SameItemError when they are one
    item and UnderFeatureError when one is under a Feature the other is not under; nothing is
    saved.
    """
    moved = parse_placed_id(item)
    other = parse_placed_id(before)
    reorder(
        item=moved,
        before=other,
        find_backlog=partial(find_backlog, store),
        load_queue=store.load_queue,
        save_queue=store.save_queue,
    )
    placed = f"{placed_text(moved)} before {placed_text(other)}"
    return Written(f"moved {placed}\n", MESSAGE.format(f"reorder {placed}"))


def show_item(item: str, store: Store) -> str:
    """The text of the work item of that id.

    Raises WorkItemIdError when the text is the id of no kind and WorkItemNotFoundError when the
    record holds no such item.
    """
    detail = store.find_work_item_detail(parse_work_item_id_of_any_kind(item))
    return show_text(bucketed(detail, store))


def add_item(
    kind: Kind,
    title: str,
    criterion: Criterion,
    description: str,
    store: Store,
    now: Now,
    parent: Parent = STANDALONE,
    depends_on: tuple[WorkItemId, ...] = (),
    filed_during: WorkItemId | None = None,
    amends: WorkItemId | None = None,
    about: tuple[str, ...] = (),
) -> Written:
    """Add a work item of that kind with its criterion; what the write says.

    It stands alone unless a Feature is given as its parent, depends on the work items given,
    is filed during the one given, amends the one given and is about the terms given. Raises
    EmptyPartError when the title is blank and CriterionError when the criterion is not of the
    form the kind takes; nothing is saved.
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
        depends_on=depends_on,
        filed_during=filed_during,
        amends=amends,
        about=about,
    )
    text = work_item_id_text(added)
    return Written(f"added {text}\n", MESSAGE.format(f"add {text}"))


def amend_item(item: str, parts: work_item.Amendment, store: Store) -> Written:
    """Rewrite the parts named of the work item in Backlog of that id; what the write says.

    A parent named puts it under that Feature or takes it out of the one it is under, both in
    Backlog; its entry in the queue stays. Raises ItemIdError naming the Feature too when the
    text is the id of no kind, or the refusal of the amend or of the move.
    """
    item_id = parse_amended_id(item)
    work_item.amend_work_item(
        item_id=item_id,
        amendment=parts,
        load_work_item=store.load_work_item,
        save_work_item=store.save_work_item,
        check_move=partial(check_move, store.features.load_feature),
    )
    text = work_item_id_text(item_id)
    return Written(f"amended {text}\n", MESSAGE.format(f"amend {text}"))


def remove_item(
    item: str,
    reason: str,
    store: Store,
    now: Now,
    superseded_by: WorkItemId | None = None,
) -> Written:
    """Remove the work item in Backlog of that id for the reason given; what the write says.

    It names the work item that supersedes it when one is given. Raises ItemIdError naming the
    Feature too when the text is the id of no kind, or the refusal of the remove.
    """
    item_id = parse_amended_id(item)
    load, save = store.load_work_item, store.save_work_item
    work_item.remove_work_item(
        item_id=item_id,
        reason=reason,
        load_work_item=load,
        save_work_item=save,
        now=now,
        superseded_by=superseded_by,
    )
    text = work_item_id_text(item_id)
    return Written(f"removed {text}\n", MESSAGE.format(f"remove {text}"))


def write_task(
    parent: str,
    title: str,
    expected_output: str,
    description: str,
    store: Store,
    now: Now,
    check: str | None = None,
) -> Written:
    """Write a Task for the work item named as parent, with its check when given; what it says.

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
        check=check,
    )
    task = task_id_text(written)
    message = MESSAGE.format(f"add {task} of {work_item_id_text(holder)}")
    return Written(f"added {task} to {parent}\n", message)
