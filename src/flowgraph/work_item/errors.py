"""The refusals of a work item that hold in every state: not found, removed, no file, no match."""

from flowgraph.work_item.id import WorkItemId, work_item_id_text


class WorkItemNotFoundError(Exception):
    """A record that holds no work item of the id asked for; `item_id` is that id."""

    def __init__(self, item_id: WorkItemId) -> None:
        super().__init__(f"no {item_id.kind.noun} {work_item_id_text(item_id)} in the record")
        self.item_id = item_id


class RemovedAlreadyError(ValueError):
    """A removed work item moved, amended or given a Task; the message names it."""

    def __init__(self, item_id: WorkItemId) -> None:
        super().__init__(f"{work_item_id_text(item_id)} is removed already")


class WorkItemFileError(Exception):
    """A file named as a work item in a record that does not hold one; names its path."""


class WorkItemMismatchError(Exception):
    """A work item read back different from the one written; its file is as it was before."""
