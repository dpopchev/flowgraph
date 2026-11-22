"""The verify command of a work item: it loads the completed item, answers its closing, saves it."""

from flowgraph.record import Now
from flowgraph.work_item.id import WorkItemId
from flowgraph.work_item.model import LoadWorkItem, SaveWorkItem
from flowgraph.work_item.moves import verified_work_item


def verify_work_item(
    *,
    item_id: WorkItemId,
    text: str,
    load_work_item: LoadWorkItem,
    save_work_item: SaveWorkItem,
    now: Now,
) -> None:
    """Keep the answer yes of the closing of the work item of that id, with the text the run of
    its criterion printed and the time now, and save it whole.

    Raises WorkItemNotFoundError when the record holds no such item, NotVerifiableError when it
    is not completed or is a Spike, VerifiedAlreadyError when it holds an answer already and
    EmptyPartError when the text is blank; nothing is saved.
    """
    save_work_item(verified_work_item(load_work_item(item_id), text, now()))
