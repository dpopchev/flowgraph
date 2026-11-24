"""What the file of a Feature holds in each of its states, told apart by its state line."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from flowgraph.item import HeldTime, KnowledgeFile


class FeatureFile(BaseModel):
    """What the file of a Feature in Backlog holds: no Task, and no time but its created one."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    about: list[str] = []
    created: HeldTime
    criteria: list[str]
    knowledge: list[KnowledgeFile] = []


class StartedFeatureFile(BaseModel):
    """What the file of a started Feature holds: its started time too."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    about: list[str] = []
    created: HeldTime
    started: HeldTime
    criteria: list[str]
    knowledge: list[KnowledgeFile] = []


class BlockedFeatureFile(BaseModel):
    """What the file of a blocked Feature holds: its started time too, and its block."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["blocked"]
    title: str
    description: str = ""
    about: list[str] = []
    created: HeldTime
    started: HeldTime
    since: HeldTime
    reason: str
    waiting_on: str
    criteria: list[str]
    knowledge: list[KnowledgeFile] = []


class CompletedFeatureFile(BaseModel):
    """What the file of a completed Feature holds: its completed time too, and its commit."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    about: list[str] = []
    created: HeldTime
    started: HeldTime
    completed: HeldTime
    commit: str = ""
    criteria: list[str]
    knowledge: list[KnowledgeFile] = []


class RemovedFeatureFile(BaseModel):
    """What the file of a removed Feature holds: its removed time and its reason, no started one."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["removed"]
    title: str
    description: str = ""
    about: list[str] = []
    created: HeldTime
    removed: HeldTime
    reason: str
    criteria: list[str]
    knowledge: list[KnowledgeFile] = []


# The file of a Feature in any of its states.
HeldFeatureFile = (
    FeatureFile
    | StartedFeatureFile
    | BlockedFeatureFile
    | CompletedFeatureFile
    | RemovedFeatureFile
)

# The validator of a Feature file, which tells the states apart by the state line.
HELD_FEATURE: TypeAdapter[HeldFeatureFile] = TypeAdapter(
    Annotated[HeldFeatureFile, Field(discriminator="state")]
)
