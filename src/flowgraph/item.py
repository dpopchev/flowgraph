"""An item of any kind, named by its id: the commands by id, run on the store of a record.

Each command reads the id, finds the kind it names and runs the work item command on the store;
a view returns the text fgraph writes, a write what it says and the message of its commit, and
each raises the refusal of the move.
"""

from dataclasses import dataclass
from functools import partial
from typing import assert_never

from flowgraph import work_item
from flowgraph.criterion import (
    NO_COMMIT,
    Commit,
    CommitNeededError,
    Criterion,
    DecisionError,
    Evidence,
    NoCommit,
    make_commit,
)
from flowgraph.development import Slug, SlugError, make_slug, slug_of_title
from flowgraph.feature.complete import complete_with_feature
from flowgraph.feature.move import check_move
from flowgraph.item_depends import bucketed
from flowgraph.item_id import (
    ItemId,
    ItemIdError,
    kind_named,
    parse_amended_id,
    parse_item_id,
    parse_placed_id,
    parse_work_item_id_of_any_kind,
)
from flowgraph.parent import STANDALONE, FeatureId, Parent, feature_id_text
from flowgraph.record import DEVELOPMENT_ENABLED, Config, Now
from flowgraph.record.queue import placed_text, reorder
from flowgraph.record.store import KINDS, Store
from flowgraph.status import BACKLOG, COMPLETED, STARTED, find_backlog, status_item
from flowgraph.task import TaskId, parse_task_id, task_id_text
from flowgraph.text import show_text
from flowgraph.work_item import Kind, WorkItemId, parse_work_item_id, work_item_id_text

# The ids of an item live in item_id.py and the listing of the status in status.py; both stay
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
    """

    out: str
    message: str
    branch: ToBranch | None = None


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


def _evidence_given(named: str, sha: str | None, config: Config) -> Evidence:
    """The evidence a complete of the item of that name gives: the commit of the sha, or none.

    The commit is the evidence of the development, so a complete needs one with it on alone.
    Raises CommitNeededError naming the option and the key when none is given then, and
    CommitError when the sha is no commit.
    """
    if sha is not None:
        return make_commit(sha)
    if config.development.enabled:
        needed = f"the development is on, {DEVELOPMENT_ENABLED} = true"
        raise CommitNeededError(f"{named} is completed with --commit: {needed}")
    return NO_COMMIT


def _completed(named: str, evidence: Evidence, feature: FeatureId | None = None) -> Written:
    """What the complete of the item of that name says: the commit it is completed at, if any.

    A Feature completed with it is named on a line of its own after it, at the same commit, and
    in the message beside it.
    """
    match evidence:
        case Commit():
            at = f" at {evidence.sha}"
        case NoCommit():
            at = ""
        case _ as unreachable:
            assert_never(unreachable)
    if feature is None:
        return Written(f"completed {named}{at}\n", MESSAGE.format(f"complete {named}"))
    with_it = feature_id_text(feature)
    out = f"completed {named}{at}\ncompleted {with_it}{at}\n"
    return Written(out, MESSAGE.format(f"complete {named} and {with_it}"))


def complete_item(
    item: str, sha: str | None, store: Store, now: Now, config: Config, decision: str | None = None
) -> Written:
    """Complete the work item or the Task of that id, in the commit given; what the write says.

    With the development on a commit is needed; with it off none is, and one given is kept. A
    Spike is completed with the decision that answers its hypothesis. The last work item of a
    started Feature completes the Feature with it, in the same write. Raises ItemIdError when
    the text is no id, CommitError when the sha is no commit, CommitNeededError when the
    development needs one, DecisionError when a Spike has no decision or another item is given
    one, or the refusal of the complete; nothing is saved.
    """
    match parse_item_id(item):
        case WorkItemId() as item_id:
            text = work_item_id_text(item_id)
            evidence = _evidence_given(text, sha, config)
            feature = complete_with_feature(item_id, evidence, decision, store, now)
            return _completed(text, evidence, feature)
        case TaskId() as task_id:
            named = task_id_text(task_id)
            if decision is not None:
                raise DecisionError(
                    f"{named} takes no decision: only a Spike is completed with one"
                )
            evidence = _evidence_given(named, sha, config)
            holder = work_item.complete_task(
                task_id=task_id,
                commit=evidence,
                load_holder=_load_holder(store),
                save_work_item=store.save_work_item,
                now=now,
            )
            return _completed(f"{named} of {work_item_id_text(holder)}", evidence)
        case _ as unreachable:
            assert_never(unreachable)
