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
class VerifiedRow:
    """The answer of the closing of a completed work item as plain data: the answer, the text
    the run printed and the time."""

    answer: str
    text: str
    on: datetime


@dataclass
class WorkItemRow:
    """One work item as plain data, as a view reads it from the record.

    A started time while started or blocked, the agent it is handed to once started, when it is,
    its block reason and what it waits on while blocked, a completed time and the commit it has
    once completed, a reason once removed. Its created time orders the
    work items of the Backlog nobody placed, its started time those of InProgress, its completed
    time those of Completed. Its Tasks are in
    the order written, each with its own state. The ids it depends on and the one it
    was filed during and the one it amends are as written, and so is the one that supersedes
    it once removed. The answer of its closing once verified, yes or no, is empty before. The ids
    it waits for are those it depends on that are not completed, set by
    the view that lists the Backlog and empty where it is not read from the whole record. It is
    the next to start when it is the first line of the Backlog its start would take, set there too.
    """

    id: str
    title: str
    state: str
    commit: str = ""
    reason: str = ""
    parent: str = ""
    complexity: str = field(default="", kw_only=True)
    created: datetime = field(kw_only=True)
    started: datetime | None = field(default=None, kw_only=True)
    agent: str = field(default="", kw_only=True)
    block_reason: str = field(default="", kw_only=True)
    waiting_on: str = field(default="", kw_only=True)
    completed: datetime | None = field(default=None, kw_only=True)
    tasks: list[TaskRow] = field(default_factory=list[TaskRow], kw_only=True)
    depends_on: list[str] = field(default_factory=list[str], kw_only=True)
    filed_during: str = field(default="", kw_only=True)
    superseded_by: str = field(default="", kw_only=True)
    amends: str = field(default="", kw_only=True)
    verified: str = field(default="", kw_only=True)
    waits_for: list[str] = field(default_factory=list[str], kw_only=True)
    next_to_start: bool = field(default=False, kw_only=True)


@dataclass
class WorkItemDetail:
    """One work item with its criterion and its Tasks as plain data, as a view reads it whole.

    The parts of its criterion are those its kind states; the others are empty. Its reason and
    what it waits on while it is blocked; its reason alone once it is removed; both empty
    otherwise.
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
    answer: str = ""
    commit: str = ""
    agent: str = ""
    reason: str = ""
    waiting_on: str = ""
    parent: str = ""
    complexity: str = ""
    knowledge: list[KnowledgeRow] = field(default_factory=list[KnowledgeRow])
    depends_on: list[DependsRow] = field(default_factory=list[DependsRow])
    filed_during: str = ""
    filed_here: list[str] = field(default_factory=list[str])
    superseded_by: str = ""
    supersedes: list[str] = field(default_factory=list[str])
    amends: str = ""
    amended_by: list[str] = field(default_factory=list[str])
    about: list[str] = field(default_factory=list[str])
    verified: VerifiedRow | None = None
