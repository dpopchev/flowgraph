"""The held file of a work item, as its TOML holds it: a model for each state and what each holds.

The relations are those of `RelationsFile`; the time, the commit, the reason and the work item that
supersedes it are held by the state that has them.
"""

from datetime import datetime
from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from flowgraph.item_file import (
    AnyCriterionFile,
    CompletedTaskFile,
    HeldTask,
    KnowledgeFile,
    TaskFile,
)
from flowgraph.work_item.depends import RelationsFile


class ItemFile(RelationsFile, BaseModel):
    """What the file of a work item in Backlog holds: its Tasks are all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    parent: str = ""
    about: list[str] = []
    created: datetime
    criterion: AnyCriterionFile
    tasks: list[TaskFile] = []
    knowledge: list[KnowledgeFile] = []


class StartedItemFile(RelationsFile, BaseModel):
    """What the file of a started work item holds: its started time, its Tasks in any state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    parent: str = ""
    about: list[str] = []
    created: datetime
    started: datetime
    criterion: AnyCriterionFile
    tasks: list[HeldTask] = []
    knowledge: list[KnowledgeFile] = []


class CompletedItemFile(RelationsFile, BaseModel):
    """What the file of a completed work item holds: the commit it has, its Tasks all completed."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    parent: str = ""
    about: list[str] = []
    created: datetime
    started: datetime
    completed: datetime
    commit: str = ""
    criterion: AnyCriterionFile
    tasks: list[CompletedTaskFile] = []
    knowledge: list[KnowledgeFile] = []


class RemovedItemFile(RelationsFile, BaseModel):
    """What the file of a removed work item holds: its removal, its Tasks all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["removed"]
    title: str
    description: str = ""
    parent: str = ""
    about: list[str] = []
    created: datetime
    removed: datetime
    reason: str = ""
    superseded_by: str = ""
    criterion: AnyCriterionFile
    tasks: list[TaskFile] = []
    knowledge: list[KnowledgeFile] = []


# The file of a work item in any of its states.
HeldItemFile = ItemFile | StartedItemFile | CompletedItemFile | RemovedItemFile

# The validator of a work item file, which tells the states apart by the state line.
HELD_ITEM: TypeAdapter[HeldItemFile] = TypeAdapter(
    Annotated[HeldItemFile, Field(discriminator="state")]
)


def commit_held(held: HeldItemFile) -> str:
    """The commit a validated file holds; empty for an item that has none."""
    match held:
        case CompletedItemFile():
            return held.commit
        case ItemFile() | StartedItemFile() | RemovedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def reason_held(held: HeldItemFile) -> str:
    """The reason a validated file holds; empty for an item not removed."""
    match held:
        case RemovedItemFile():
            return held.reason
        case ItemFile() | StartedItemFile() | CompletedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def started_held(held: HeldItemFile) -> datetime | None:
    """The started time a validated file of a started item holds; none in any other state."""
    match held:
        case StartedItemFile():
            return held.started
        case ItemFile() | CompletedItemFile() | RemovedItemFile():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def completed_held(held: HeldItemFile) -> datetime | None:
    """The completed time a validated file holds; none for an item not completed."""
    match held:
        case CompletedItemFile():
            return held.completed
        case ItemFile() | StartedItemFile() | RemovedItemFile():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def superseded_held(held: HeldItemFile) -> str:
    """The id of the work item that supersedes a validated file's item; empty for none."""
    match held:
        case RemovedItemFile():
            return held.superseded_by
        case ItemFile() | StartedItemFile() | CompletedItemFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
