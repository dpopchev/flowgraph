"""The views of a work item: the plain data a view reads from the record, a row and a detail."""

from dataclasses import dataclass, field
from datetime import datetime

from flowgraph.knowledge import KnowledgeRow
from flowgraph.task import TaskRow


@dataclass
class WorkItemRow:
    """One work item as plain data, as a view reads it from the record.

    A started time while started, a completed time and the commit it has once completed, a reason
    once removed. Its created time orders the work items of the Backlog nobody placed, its
    started time those of InProgress, its completed time those of Completed. Its Tasks are in
    the order written, each with its own state.
    """

    id: str
    title: str
    state: str
    commit: str = ""
    reason: str = ""
    parent: str = ""
    created: datetime = field(kw_only=True)
    started: datetime | None = field(default=None, kw_only=True)
    completed: datetime | None = field(default=None, kw_only=True)
    tasks: list[TaskRow] = field(default_factory=list[TaskRow], kw_only=True)


@dataclass
class WorkItemDetail:
    """One work item with its criterion and its Tasks as plain data, as a view reads it whole.

    The parts of its criterion are those its kind states; the others are empty.
    """

    id: str
    title: str
    state: str
    description: str
    tasks: list[TaskRow]
    given: str = ""
    when: str = ""
    then: str = ""
    observed: str = ""
    expected: str = ""
    hypothesis: str = ""
    decision: str = ""
    commit: str = ""
    reason: str = ""
    parent: str = ""
    knowledge: list[KnowledgeRow] = field(default_factory=list[KnowledgeRow])
