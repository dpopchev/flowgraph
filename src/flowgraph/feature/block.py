"""The block of a Feature and its unblock, beside those of a work item and of a Task.

A Feature is to its work items what a work item is to its Tasks: a started one that cannot go
on is blocked, with its reason and what it waits on, and unblocked back to started. While it is
blocked no further work item of it starts (`flowgraph.feature.start`) and its started one goes
on; its unblock starts the next one when none is started, as the completion of one does
(`flowgraph.feature.next`). Each runs on the store of a record, as the commands of a work item
do (`flowgraph.item.commands`).
"""

from typing import assert_never

from flowgraph.feature import blocked_feature, unblocked_feature
from flowgraph.feature.next import NOT_STARTED, start_next
from flowgraph.feature.start import first_in_backlog
from flowgraph.item.commands import MESSAGE, Written
from flowgraph.item.id import parse_moved_id
from flowgraph.item.moves import block_item, unblock_item
from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.record import Config, Now
from flowgraph.record.store import Store
from flowgraph.status import rows_by_id
from flowgraph.task import TaskId
from flowgraph.work_item import IN_PROGRESS, WorkItemId, work_item_id_text


def _feature_of(item: str) -> FeatureId | None:
    """The Feature the id names; None for the id of a work item or of a Task.

    Raises ItemIdError naming every kind when the text is the id of none, and the refusal of an
    id below 1 of its kind.
    """
    match parse_moved_id(item):
        case FeatureId() as feature_id:
            return feature_id
        case WorkItemId() | TaskId():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def block_named(item: str, reason: str, waiting_on: str, store: Store, now: Now) -> Written:
    """Block the started Feature, work item or Task of that id for the reason; what the write says.

    Raises ItemIdError when the text is the id of none, FeatureNotFoundError when the record
    holds no such Feature, NotStartedError when it is in Backlog, BlockedError when it is
    blocked already, CompletedAlreadyError when it is completed and EmptyPartError when the
    reason or what it waits on is blank; for a work item or a Task the refusal of `block_item`.
    Nothing is saved.
    """
    feature_id = _feature_of(item)
    if feature_id is None:
        return block_item(item, reason, waiting_on, store, now)
    held = store.features.load_feature(feature_id)
    store.features.save_feature(blocked_feature(held, reason, waiting_on, now()))
    named = feature_id_text(feature_id)
    return Written(f"blocked {named}\n", MESSAGE.format(f"block {named}"))


def _next_of(feature_id: FeatureId, store: Store) -> WorkItemId | None:
    """The work item the unblock of the Feature starts; None when it starts none.

    It is its first work item in Backlog in the order of the queue, unless one of it is started
    or blocked: the unblock restarts a Feature that holds work, and starts one only when none is.
    """
    named = feature_id_text(feature_id)
    under = (row for row in rows_by_id(store).values() if row.parent == named)
    if any(row.state in IN_PROGRESS for row in under):
        return None
    return first_in_backlog(feature_id, store)


def unblock_named(item: str, store: Store, now: Now, config: Config) -> Written:
    """Unblock the blocked Feature, work item or Task of that id; what the write says.

    A Feature is started again and, when no work item of it is started, starts its next one:
    named on a line of its own after the unblock and in the message beside it, with the branch
    to check out at the commit of the write. A next work item that cannot start is named on
    that line with why, and the unblock stands as written. Raises ItemIdError when the text is
    the id of none, FeatureNotFoundError when the record holds no such Feature and
    NotBlockedError when it is not blocked; for a work item or a Task the refusal of
    `unblock_item`. Nothing is saved.
    """
    feature_id = _feature_of(item)
    if feature_id is None:
        return unblock_item(item, store)
    store.features.save_feature(unblocked_feature(store.features.load_feature(feature_id)))
    named = feature_id_text(feature_id)
    unblocked = Written(f"unblocked {named}\n", MESSAGE.format(f"unblock {named}"))
    following = _next_of(feature_id, store)
    if following is None:
        return unblocked
    try:
        started = start_next(following, store, now, config)
    except NOT_STARTED as error:
        return Written(f"{unblocked.out}not started: {error}\n", unblocked.message)
    both = f"unblock {named} and start {work_item_id_text(following)}"
    return Written(unblocked.out + started.out, MESSAGE.format(both), started.branch)
