"""The verify command by id: it keeps the answer of a closing on a completed work item.

A no adds, in the same write, the Bug that amends the work item. It runs on the store of a
record, as the commands of a work item do (`flowgraph.item.commands`).
"""

from functools import partial
from typing import assert_never

from flowgraph import work_item
from flowgraph.bug import BUG
from flowgraph.feature import FeatureRemovedError
from flowgraph.feature.item import parent_named
from flowgraph.item.commands import MESSAGE, Written
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.parent import STANDALONE, FeatureId, Parent, Standalone, feature_id_text
from flowgraph.record import Now
from flowgraph.record.store import Store
from flowgraph.task import CompletedAlreadyError
from flowgraph.work_item import NotVerifiableError, WorkItemId, WorkItemIdError, work_item_id_text
from flowgraph.work_item.verification import TAKES


def _verified_id(item: str) -> WorkItemId:
    """The id of the work item to verify; raises NotVerifiableError when the text is none."""
    try:
        return parse_work_item_id_of_any_kind(item)
    except WorkItemIdError:
        raise NotVerifiableError(f"{item!r} is no work item id: {TAKES}") from None


def verify_item(item: str, text: str, store: Store, now: Now) -> Written:
    """Keep the answer yes of the closing of the work item of that id, with what the run printed.

    Returns what the write says. Raises NotVerifiableError when the text is the id of a Task, a
    Feature or no item, or the item is not completed or is a Spike, WorkItemNotFoundError when the
    record holds no such item, VerifiedAlreadyError when it holds an answer already and
    EmptyPartError when the text is blank; nothing is saved.
    """
    item_id = _verified_id(item)
    work_item.verify_work_item(
        item_id=item_id,
        text=text,
        load_work_item=store.load_work_item,
        save_work_item=store.save_work_item,
        now=now,
    )
    named = work_item_id_text(item_id)
    return Written(f"verified {named}\n", MESSAGE.format(f"verify {named}"))


def _joined(store: Store, parent: Parent) -> Parent:
    """The parent of the Bug a no files: the Feature of the work item, as `fgraph add` takes it,
    or standing alone when that Feature is completed or removed."""
    match parent:
        case Standalone():
            return STANDALONE
        case FeatureId():
            try:
                return parent_named(feature_id_text(parent), store)
            except CompletedAlreadyError, FeatureRemovedError:
                return STANDALONE
        case _ as unreachable:
            assert_never(unreachable)


def verify_item_no(item: str, text: str, store: Store, now: Now) -> Written:
    """Keep the answer no of the closing of the work item of that id and add the Bug it files.

    The Bug takes the next Bug id of the record and joins the Feature of the work item while it
    is not completed. The two are one write: a failure after the first save puts every file of
    the record back as it was, and the failure is raised. Returns what the write says, both ids.
    Raises the refusals of `verify_item` before anything is saved.
    """
    item_id = _verified_id(item)
    try:
        added = work_item.verify_work_item_no(
            item_id=item_id,
            text=text,
            bug=BUG,
            find_bug_rows=partial(store.find_work_item_rows, BUG),
            join=partial(_joined, store),
            load_work_item=store.load_work_item,
            save_work_item=store.save_work_item,
            now=now,
        )
    except Exception:
        store.restore_files()
        raise
    named, bug = work_item_id_text(item_id), work_item_id_text(added)
    return Written(
        f"verified {named} no\nadded {bug} amending {named}\n",
        MESSAGE.format(f"verify {named} no and add {bug}"),
    )
