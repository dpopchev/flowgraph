"""The verify command by id: it keeps the answer of a closing on a completed work item.

It runs on the store of a record, as the commands of a work item do (`flowgraph.item.commands`).
"""

from flowgraph import work_item
from flowgraph.item.commands import MESSAGE, Written
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.record import Now
from flowgraph.record.store import Store
from flowgraph.work_item import NotVerifiableError, WorkItemIdError, work_item_id_text
from flowgraph.work_item.verification import TAKES


def verify_item(item: str, text: str, store: Store, now: Now) -> Written:
    """Keep the answer yes of the closing of the work item of that id, with what the run printed.

    Returns what the write says. Raises NotVerifiableError when the text is the id of a Task, a
    Feature or no item, or the item is not completed or is a Spike, WorkItemNotFoundError when the
    record holds no such item, VerifiedAlreadyError when it holds an answer already and
    EmptyPartError when the text is blank; nothing is saved.
    """
    try:
        item_id = parse_work_item_id_of_any_kind(item)
    except WorkItemIdError:
        raise NotVerifiableError(f"{item!r} is no work item id: {TAKES}") from None
    work_item.verify_work_item(
        item_id=item_id,
        text=text,
        load_work_item=store.load_work_item,
        save_work_item=store.save_work_item,
        now=now,
    )
    named = work_item_id_text(item_id)
    return Written(f"verified {named}\n", MESSAGE.format(f"verify {named}"))
