"""The layers a configuration turns on, each a value: the commits, the development, the delivery.

The development holds its keys as values too: the limit of the work items started at once, how
a landing merges and the gate it runs. The delivery holds the steps a landing takes after it:
the push of main and the tag at the close of a Feature.
"""

from dataclasses import dataclass, field
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
    PULL_REQUEST = "pull-request"


class Driver(Enum):
    """Who drives the development: a developer by default, or an agent; each is its file word."""

    DEVELOPER = "developer"
    AGENT = "agent"


class Mode(Enum):
    """Where a work item is developed: on its own branch, or on main; each is its file word.

    `branch` makes a branch and a worktree at its start and merges it at its landing; `trunk` makes
    none: the work item is started, worked and completed on main, one at a time.
    """

    BRANCH = "branch"
    TRUNK = "trunk"


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

    The limit, the merge, the gate, the driver and the mode are keys of the development: none says
    anything while it is off.
    """

    enabled: bool
    parallel: Limit
    merge: Merge
    gate: Gate
    driver: Driver = field(default=Driver.DEVELOPER, kw_only=True)
    mode: Mode = field(default=Mode.BRANCH, kw_only=True)


def branched(development: Development) -> bool:
    """Whether the start of a work item makes its branch: the development on, the mode branch."""
    return development.enabled and development.mode is Mode.BRANCH


class TagAt(Enum):
    """Which closes a landing tags main at; each is its word in the file.

    `feature-close` tags the close of a Feature alone; `close` tags that and a work item that
    stands alone at its landing; `none` tags nothing.
    """

    FEATURE_CLOSE = "feature-close"
    CLOSE = "close"
    NONE = "none"


@dataclass(frozen=True)
class Delivery:
    """What a landing takes after the write that completes its work item.

    Main pushed, or not; and main tagged with its next version at the close its `tag` names: a
    Feature, a work item that stands alone too, or never. A step of a landing, so it says
    nothing while the development is off.
    """

    push: bool
    tag: TagAt
