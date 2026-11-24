"""The pointer of a record to the archive of board 1: `[archive] board` of config.toml.

A repository that adopts fgraph keeps the `.board/` of board 1 whole beside the new record, which
holds a pointer to it; fgraph reads no file of the archive and writes none (the Decision on
S-0120 of 2026-11-23).
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

# The key that points at the `.board/` of board 1, as a refusal names it.
ARCHIVE_BOARD = "archive.board"


@dataclass(frozen=True)
class Archived:
    """The record points at the `.board/` of board 1: its path as written."""

    board: str


@dataclass(frozen=True)
class Unarchived:
    """No archive: a value of the pointer, not a missing one."""


# The one value of no archive.
UNARCHIVED = Unarchived()

# Where the board 1 of the repository is kept: at that path, or nowhere.
Archive = Archived | Unarchived


class ArchiveTable(BaseModel):
    """What `[archive]` holds; a key left out is its default.

    Its own strict, closed model: this module cannot import `flowgraph.record.config`, which
    imports it.
    """

    model_config = ConfigDict(extra="forbid", strict=True)

    # A path that holds a character other than a blank.
    board: str | None = Field(default=None, pattern=r"\S")


def make_archive(table: ArchiveTable) -> Archive:
    """The archive the table points at: none when it holds no board."""
    return UNARCHIVED if table.board is None else Archived(table.board)
