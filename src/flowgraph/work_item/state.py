"""The state of a work item or a Task as the record writes it, and the commit it holds."""

from typing import assert_never

from flowgraph.criterion import evidence_text
from flowgraph.task import BlockedTask, CompletedTask, RemovedTask, StartedTask, Task, TaskState
from flowgraph.work_item.model import (
    BlockedWorkItem,
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
)

# The state of a started work item or Task, as the record writes it: its one name.
STARTED = "started"

# The state of a blocked work item or Task, as the record writes it.
BLOCKED = "blocked"

# The states listed under InProgress: a started work item and a blocked one.
IN_PROGRESS = frozenset({STARTED, BLOCKED})


def state_name(item: WorkItemState | TaskState) -> str:
    """The state of a work item or a Task as the record writes it."""
    match item:
        case WorkItem() | Task():
            return "backlog"
        case StartedWorkItem() | StartedTask():
            return STARTED
        case BlockedWorkItem() | BlockedTask():
            return BLOCKED
        case CompletedWorkItem() | CompletedTask():
            return "completed"
        case RemovedWorkItem() | RemovedTask():
            return "removed"
        case _ as unreachable:
            assert_never(unreachable)


def commit_sha(item: WorkItemState | TaskState) -> str:
    """The sha of the commit of a completed work item or Task; empty for one that has none."""
    match item:
        case CompletedWorkItem() | CompletedTask():
            return evidence_text(item.commit)
        case WorkItem() | StartedWorkItem() | BlockedWorkItem() | RemovedWorkItem():
            return ""
        case Task() | StartedTask() | BlockedTask() | RemovedTask():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
