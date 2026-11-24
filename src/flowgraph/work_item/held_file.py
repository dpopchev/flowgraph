"""The held file of a work item, as its TOML holds it: a model for each state and what each holds.

The relations are those of `RelationsFile`; the time, the commit, the reason and the work item that
supersedes it are held by the state that has them.
"""

from datetime import datetime
from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, TypeAdapter

from flowgraph.item import (
    AnyCriterionFile,
    CompletedTaskFile,
    HeldTask,
    HeldTime,
    KnowledgeFile,
    TaskFile,
)
from flowgraph.work_item.complexity import Complexity
from flowgraph.work_item.depends import RelationsFile
from flowgraph.work_item.progress_file import ProgressTables
from flowgraph.work_item.verification import Verdict


class ItemFile(RelationsFile, ProgressTables, BaseModel):
    """What the file of a work item in Backlog holds: its Tasks are all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    parent: str = ""
    realizes: PositiveInt | None = None
    about: list[str] = []
    complexity: Complexity | None = None
    created: HeldTime
    criterion: AnyCriterionFile
    tasks: list[TaskFile] = []
    knowledge: list[KnowledgeFile] = []


class StartedItemFile(RelationsFile, ProgressTables, BaseModel):
    """What the file of a started work item holds: its started time, its Tasks in any state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    parent: str = ""
    realizes: PositiveInt | None = None
    about: list[str] = []
    complexity: Complexity | None = None
    created: HeldTime
    started: HeldTime
    agent: str = ""
    criterion: AnyCriterionFile
    tasks: list[HeldTask] = []
    knowledge: list[KnowledgeFile] = []


class BlockedItemFile(RelationsFile, ProgressTables, BaseModel):
    """What the file of a blocked work item holds: what a started one does, then its block."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["blocked"]
    title: str
    description: str = ""
    parent: str = ""
    realizes: PositiveInt | None = None
    about: list[str] = []
    complexity: Complexity | None = None
    created: HeldTime
    started: HeldTime
    since: HeldTime
    reason: str
    waiting_on: str
    agent: str = ""
    criterion: AnyCriterionFile
    tasks: list[HeldTask] = []
    knowledge: list[KnowledgeFile] = []


class VerifiedFile(BaseModel):
    """The table of the answer of a closing: the answer, what the run printed and the time."""

    model_config = ConfigDict(extra="forbid")

    answer: Verdict
    text: str
    on: HeldTime


class CompletedItemFile(RelationsFile, ProgressTables, BaseModel):
    """What the file of a completed work item holds: the commit it has, its Tasks all completed.

    The answer of its closing is held once it has one; a file written before holds none.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    parent: str = ""
    realizes: PositiveInt | None = None
    about: list[str] = []
    complexity: Complexity | None = None
    created: HeldTime
    started: HeldTime
    completed: HeldTime
    agent: str = ""
    commit: str = ""
    verified: VerifiedFile | None = None
    criterion: AnyCriterionFile
    tasks: list[CompletedTaskFile] = []
    knowledge: list[KnowledgeFile] = []


class RemovedItemFile(RelationsFile, ProgressTables, BaseModel):
    """What the file of a removed work item holds: its removal, its Tasks all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["removed"]
    title: str
    description: str = ""
    parent: str = ""
    realizes: PositiveInt | None = None
    about: list[str] = []
    complexity: Complexity | None = None
    created: HeldTime
    removed: HeldTime
    reason: str = ""
    superseded_by: str = ""
    criterion: AnyCriterionFile
    tasks: list[TaskFile] = []
    knowledge: list[KnowledgeFile] = []


# The file of a work item in any of its states.
HeldItemFile = ItemFile | StartedItemFile | BlockedItemFile | CompletedItemFile | RemovedItemFile

# The validator of a work item file, which tells the states apart by the state line.
HELD_ITEM: TypeAdapter[HeldItemFile] = TypeAdapter(
    Annotated[HeldItemFile, Field(discriminator="state")]
)


def commit_held(held: HeldItemFile) -> str:
    """The commit a validated file holds; empty for an item that has none."""
    match held:
        case CompletedItemFile():
            return held.commit
        case ItemFile() | StartedItemFile() | BlockedItemFile() | RemovedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def reason_held(held: HeldItemFile) -> str:
    """The reason a validated file holds; empty for an item not removed, the block kept apart."""
    match held:
        case RemovedItemFile():
            return held.reason
        case ItemFile() | StartedItemFile() | BlockedItemFile() | CompletedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def started_held(held: HeldItemFile) -> datetime | None:
    """The started time a validated file of a started or blocked item holds; none in any other."""
    match held:
        case StartedItemFile() | BlockedItemFile():
            return held.started
        case ItemFile() | CompletedItemFile() | RemovedItemFile():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def agent_held(held: HeldItemFile) -> str:
    """The agent a validated file of a started, blocked or completed item holds; empty for none."""
    match held:
        case StartedItemFile() | BlockedItemFile() | CompletedItemFile():
            return held.agent
        case ItemFile() | RemovedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def completed_held(held: HeldItemFile) -> datetime | None:
    """The completed time a validated file holds; none for an item not completed."""
    match held:
        case CompletedItemFile():
            return held.completed
        case ItemFile() | StartedItemFile() | BlockedItemFile() | RemovedItemFile():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def verified_held(held: HeldItemFile) -> VerifiedFile | None:
    """The answer of the closing a validated file holds; none for an item without one."""
    match held:
        case CompletedItemFile():
            return held.verified
        case ItemFile() | StartedItemFile() | BlockedItemFile() | RemovedItemFile():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def superseded_held(held: HeldItemFile) -> str:
    """The id of the work item that supersedes a validated file's item; empty for none."""
    match held:
        case RemovedItemFile():
            return held.superseded_by
        case ItemFile() | StartedItemFile() | BlockedItemFile() | CompletedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def block_held(held: HeldItemFile) -> tuple[str, str]:
    """The reason and what it waits on the file of a blocked item holds; both empty for others."""
    match held:
        case BlockedItemFile():
            return held.reason, held.waiting_on
        case ItemFile() | StartedItemFile() | CompletedItemFile() | RemovedItemFile():
            return "", ""
        case _ as unreachable:
            assert_never(unreachable)
