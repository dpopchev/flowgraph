"""The pointer of a record to the archive of board 1: `[archive] board` of config.toml.

A repository that adopts fgraph keeps the `.board/` of board 1 whole beside the new record, which
holds a pointer to it; fgraph reads no file of the archive and writes none (the Decision on
S-0120 of 2026-11-23).
"""

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

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


class ArchivedError(ValueError):
    """An id of board 1 asked of a record that points at its archive: where, and how to show it."""


# The id of board 1 as a command hands it over: the letter, a dash, a number of 1 or more.
_OLD_ID = re.compile(r"([EWTewt])-0*([1-9][0-9]*)")

# The command of board 1 that shows an item, and the line that names the archive and that command.
COMMAND = "uv run ~/.claude/skills/board/scripts/board.py --root {root} show {old}"
LINE = "{old} is in the archive of board 1 at {where} -- show it with: {command}"


def old_id(text: str) -> str | None:
    """The id as board 1 writes it, three digits at least; None for any other text."""
    found = _OLD_ID.fullmatch(text)
    return None if found is None else f"{found[1].upper()}-{int(found[2]):03d}"


def check_archived(text: str, archive: Archive, record: Path) -> None:
    """Return when the text is no id of board 1 or the record points at no archive.

    Raises ArchivedError otherwise, naming the id as board 1 wrote it, the archive and the command
    that shows it. T needs the rule: `flowgraph.parser.ids` reads T-456 as T-0456 before any
    command sees it, board 1 writes T-456 and T-1364, and `fgraph show` takes no Task, so under
    a pointer every T id asked of show is named as the old one. It takes no callable and opens
    nothing: that is how fgraph never reads board 1.
    """
    match archive:
        case Unarchived():
            return
        case Archived(board):
            old = old_id(text)
            if old is None:
                return
            where = record.parent / board
            root = shlex.quote(str(where.parent))
            raise ArchivedError(
                LINE.format(old=old, where=where, command=COMMAND.format(root=root, old=old))
            )
        case _ as unreachable:
            assert_never(unreachable)
