"""An Upkeep: work that keeps a behavior, the kind of work item whose ids are written `U-0001`.

Each Upkeep name stands for the name of the shared work item (`flowgraph.work_item`).
"""

from collections.abc import Collection

from flowgraph.work_item import (
    CompletedWorkItem,
    FindWorkItemRows,
    LoadWorkItem,
    OpenWorkItem,
    SaveWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemDetail,
    WorkItemFileError,
    WorkItemId,
    WorkItemIdError,
    WorkItemMismatchError,
    WorkItemNotFoundError,
    WorkItemRow,
    WorkItemState,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    next_work_item_id,
    parse_work_item_id,
    started_work_item,
    work_item_detail,
    work_item_id_text,
    work_item_row,
)

# The kind of an Upkeep.
UPKEEP = make_kind("Upkeep", "an", "U")

UpkeepId = WorkItemId
Upkeep = WorkItem
StartedUpkeep = StartedWorkItem
CompletedUpkeep = CompletedWorkItem
OpenUpkeep = OpenWorkItem
UpkeepState = WorkItemState
UpkeepRow = WorkItemRow
UpkeepDetail = WorkItemDetail
FindUpkeepRows = FindWorkItemRows
LoadUpkeep = LoadWorkItem
SaveUpkeep = SaveWorkItem
UpkeepIdError = WorkItemIdError
UpkeepNotFoundError = WorkItemNotFoundError
UpkeepFileError = WorkItemFileError
UpkeepMismatchError = WorkItemMismatchError

make_upkeep = make_work_item
started_upkeep = started_work_item
completed_upkeep = completed_work_item
upkeep_id_text = work_item_id_text
upkeep_row = work_item_row
upkeep_detail = work_item_detail


def make_upkeep_id(number: int) -> UpkeepId:
    """The id of the Upkeep with that number; raises UpkeepIdError when it is below 1."""
    return make_work_item_id(UPKEEP, number)


def parse_upkeep_id(text: str) -> UpkeepId:
    """The Upkeep id written as the text; raises UpkeepIdError when it is not `U-` and a number."""
    return parse_work_item_id(UPKEEP, text)


def next_upkeep_id(taken: Collection[UpkeepId]) -> UpkeepId:
    """The next free Upkeep id: one above the highest taken, the first when none is."""
    return next_work_item_id(UPKEEP, taken)
