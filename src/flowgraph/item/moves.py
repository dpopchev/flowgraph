"""The moves of an item named by its id: its start, the block and unblock of a Task, its complete.

Each reads the id, runs the move of the work item or of the Task on the store and returns what
the write says with the message of its commit; each raises the refusal of the move.
"""

from typing import assert_never

from flowgraph import work_item
from flowgraph.criterion import (
    NO_COMMIT,
    Commit,
    CommitNeededError,
    DecisionError,
    Evidence,
    NoCommit,
    make_commit,
)
from flowgraph.development import SlugError, make_slug, slug_of_title
from flowgraph.feature.complete import complete_with_feature
from flowgraph.item.commands import MESSAGE, ToBranch, Written
from flowgraph.item.id import parse_item_id
from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.record import DEVELOPMENT_ENABLED, Config, Now
from flowgraph.record.store import KINDS, Store
from flowgraph.task import TaskId, parse_task_id, task_id_text
from flowgraph.work_item import WorkItemId, parse_work_item_id, work_item_id_text


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
