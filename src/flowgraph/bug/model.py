"""A Bug: a behavior that fails, the kind of work item whose ids are written `B-0001`.

Its criterion is what is observed and what is expected instead. Each Bug name stands for the
name of the shared work item (`flowgraph.work_item`).
"""

from collections.abc import Collection

from flowgraph.criterion import Defect
from flowgraph.work_item import (
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemId,
    WorkItemIdError,
    WorkItemState,
    make_kind,
    make_work_item,
    make_work_item_id,
    next_work_item_id,
    parse_work_item_id,
    work_item_id_text,
)

# The kind of a Bug.
BUG = make_kind("Bug", "a", "B", Defect)

BugId = WorkItemId
Bug = WorkItem
StartedBug = StartedWorkItem
CompletedBug = CompletedWorkItem
RemovedBug = RemovedWorkItem
BugState = WorkItemState
BugIdError = WorkItemIdError

make_bug = make_work_item
bug_id_text = work_item_id_text


def make_bug_id(number: int) -> BugId:
    """The id of the Bug with that number; raises BugIdError when it is below 1."""
    return make_work_item_id(BUG, number)


def parse_bug_id(text: str) -> BugId:
    """The Bug id written as the text; raises BugIdError when it is not `B-` and a number."""
    return parse_work_item_id(BUG, text)


def next_bug_id(taken: Collection[BugId]) -> BugId:
    """The next free Bug id: one above the highest taken, the first when none is."""
    return next_work_item_id(BUG, taken)
