"""The layers a configuration turns on, each a value: the commits, the development, the delivery.

The development holds its keys as values too: the limit of the work items started at once, how
a landing merges and the gate it runs. The delivery holds the steps a landing takes after it.
"""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Git:
    """The commits of the record: fgraph commits every write of it, or none."""

    commit: bool


@dataclass(frozen=True)
class Parallel:
    """The most work items started at once: a whole number of 1 or more."""

    most: int


@dataclass(frozen=True)
class Unlimited:
    """No limit of the work items started at once: a value of the limit, not a missing one."""


# The one value of no limit.
UNLIMITED = Unlimited()

# How many work items are started at once: at most that many, or as many as are started.
Limit = Parallel | Unlimited


class Merge(Enum):
    """How a landing merges the branch of a work item into main; each is its word in the file."""

    MERGE_COMMIT = "merge-commit"
    SQUASH = "squash"
    FAST_FORWARD = "fast-forward"


@dataclass(frozen=True)
class Gated:
    """The gate of a landing: one command line, run through the shell, never a blank one."""

    command: str


@dataclass(frozen=True)
class Ungated:
    """No gate of a landing: a value of the gate, not a missing one."""


# The one value of no gate.
UNGATED = Ungated()

# What a landing runs before main moves: that command, or nothing.
Gate = Gated | Ungated


@dataclass(frozen=True)
class Development:
    """The development beside the source code: turned on, or off, and its keys as written.

    The limit, the merge and the gate are keys of the development: none says anything while it
    is off.
    """

    enabled: bool
    parallel: Limit
    merge: Merge
    gate: Gate


@dataclass(frozen=True)
class Delivery:
    """What a landing takes after the write that completes its work item: main pushed, or not.

    A step of a landing, so it says nothing while the development is off.
    """

    push: bool
