"""The views of a work item: the plain data a view reads from the record, a row and a detail."""

from dataclasses import dataclass, field
from datetime import datetime

from flowgraph.knowledge import KnowledgeRow
from flowgraph.task import TaskRow


@dataclass
class DependsRow:
    """A work item another one depends on as plain data: its id, and the bucket it is listed in.

    The bucket is empty where it is not read from the record, as in the file of the item.
    """

    id: str
    bucket: str = ""


@dataclass
class WorkItemRow:
    """One work item as plain data, as a view reads it from the record.

    A started time while started, a completed time and the commit it has once completed, a reason
    once removed. Its created time orders the work items of the Backlog nobody placed, its
    started time those of InProgress, its completed time those of Completed. Its Tasks are in
    the order written, each with its own state. The ids it depends on and the one it
    was filed during are as written.
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
    depends_on: list[str] = field(default_factory=list[str], kw_only=True)
    filed_during: str = field(default="", kw_only=True)


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
    depends_on: list[DependsRow] = field(default_factory=list[DependsRow])
    filed_during: str = ""
    filed_here: list[str] = field(default_factory=list[str])
