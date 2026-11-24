"""The lines each bucket lists and the buckets a frame shows: `[status]` and `[watch]`.

`[status]` says how many lines `fgraph status` and `fgraph watch` list under each bucket, a count
of 1 or more or all; `[watch] buckets` names the buckets a frame of `fgraph watch` shows (the
Decision on S-0136 of 2026-11-23). The tables are strict, closed models, as the archive is: this
module cannot import `flowgraph.record.config`, which imports it.
"""

from dataclasses import dataclass
from enum import Enum
from typing import assert_never

from pydantic import BaseModel, ConfigDict, Field, field_validator

# The key of each bucket's count of lines, and the key of the buckets a frame shows.
STATUS_BACKLOG = "status.backlog"
STATUS_IN_PROGRESS = "status.in-progress"
STATUS_COMPLETED = "status.completed"
STATUS_REMOVED = "status.removed"
WATCH_BUCKETS = "watch.buckets"

# The word of every line of a bucket.
ALL = "all"

# What a key of lines takes, and what the key of the buckets takes.
LINES_TAKEN = "a count of lines of 1 or more, or all"
BUCKETS_TAKEN = (
    "the buckets to show, among backlog, in-progress, completed and removed, separated by commas"
)

# What each key takes, by its dotted name.
TAKES = {
    STATUS_BACKLOG: LINES_TAKEN,
    STATUS_IN_PROGRESS: LINES_TAKEN,
    STATUS_COMPLETED: LINES_TAKEN,
    STATUS_REMOVED: LINES_TAKEN,
    WATCH_BUCKETS: BUCKETS_TAKEN,
}


class Bucket(Enum):
    """A bucket of the flow, in the order of the flow; each is its word in the file."""

    BACKLOG = "backlog"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    REMOVED = "removed"


@dataclass(frozen=True)
class Lines:
    """The most lines a bucket lists: a whole number of 1 or more."""

    count: int


@dataclass(frozen=True)
class AllLines:
    """Every line of a bucket: a value of the count, not a missing one."""


# The one value of every line.
ALL_LINES = AllLines()

# How many lines a bucket lists: at most that many, or every one.
Listed = Lines | AllLines


@dataclass(frozen=True)
class StatusLists:
    """The lines each bucket lists, as the configuration sets them."""

    backlog: Listed
    in_progress: Listed
    completed: Listed
    removed: Listed


@dataclass(frozen=True)
class WatchShows:
    """The buckets a frame of watch shows, in the order of the flow."""

    buckets: tuple[Bucket, ...]


def _lines(value: object) -> int | str:
    """The value when it is all or a whole number of 1 or more, no bool; raises ValueError."""
    if value == ALL and isinstance(value, str):
        return ALL
    if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
        return value
    raise ValueError(LINES_TAKEN)


def _words(value: object) -> list[str]:
    """The words of the text, each a bucket, none twice; raises ValueError otherwise."""
    if not isinstance(value, str):
        raise ValueError(BUCKETS_TAKEN)
    words = [word.strip() for word in value.split(",")]
    named = {bucket.value for bucket in Bucket}
    if any(word not in named for word in words) or len(set(words)) != len(words):
        raise ValueError(BUCKETS_TAKEN)
    return words


class StatusTable(BaseModel):
    """What `[status]` holds; a key left out is its default.

    One value that is no type of its own: a count of 1 or more or the text all, read by one
    validator, so a refusal names the key.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    backlog: int | str = 1
    in_progress: int | str = Field(default=ALL, alias="in-progress")
    completed: int | str = 5
    removed: int | str = 5

    @field_validator("backlog", "in_progress", "completed", "removed", mode="plain")
    @classmethod
    def _checked(cls, value: object) -> int | str:
        return _lines(value)


class WatchTable(BaseModel):
    """What `[watch]` holds; a key left out is its default: the four buckets."""

    model_config = ConfigDict(extra="forbid", strict=True)

    buckets: str = ", ".join(bucket.value for bucket in Bucket)

    @field_validator("buckets", mode="plain")
    @classmethod
    def _checked(cls, value: object) -> str:
        _words(value)
        return str(value)


def _listed(value: int | str) -> Listed:
    """The count of lines the value names: all for the text, that many lines for a count."""
    return ALL_LINES if isinstance(value, str) else Lines(value)


def make_status_lists(table: StatusTable) -> StatusLists:
    """The lines each bucket lists, as the table sets them."""
    return StatusLists(
        _listed(table.backlog),
        _listed(table.in_progress),
        _listed(table.completed),
        _listed(table.removed),
    )


def make_watch_shows(table: WatchTable) -> WatchShows:
    """The buckets the table names, in the order of the flow whatever the order written."""
    named = set(_words(table.buckets))
    return WatchShows(tuple(bucket for bucket in Bucket if bucket.value in named))


def listed_text(listed: Listed) -> int | str:
    """The count of lines as the file writes it: the number, or the text all."""
    match listed:
        case Lines(count):
            return count
        case AllLines():
            return ALL
        case _ as unreachable:
            assert_never(unreachable)


def buckets_text(shows: WatchShows) -> str:
    """The buckets as the file writes them: their words, in order, joined by a comma and a blank."""
    return ", ".join(bucket.value for bucket in shows.buckets)
