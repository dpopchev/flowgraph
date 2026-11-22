"""A term of the project: a node of the record with no flow, kept as one file, `terms/gate.toml`.

A term is the name of a thing the project talks about and what it means. Its name is its id:
lowercase words of letters and digits joined by `-`, never one that reads as the id of an item.
It is in no bucket and no queue, since nothing is done to it: it is added and then it stands.
"""

import re
import tomllib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from flowgraph.criterion import EmptyPartError, said
from flowgraph.item_file import write_checked

# The directory of every term inside a record, one file per term, named by its name.
TERMS = "terms"

# A name: words of lowercase letters and digits, joined by one dash.
NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

# What reads as the id of an item: letters, a dash and a number, as F-0001 or S-0001.
ITEM_ID = re.compile(r"[A-Za-z]+-\d+")


class TermError(ValueError):
    """A name that is no term name, or that reads as the id of an item."""


class TermNotFoundError(Exception):
    """A record that holds no term of the name asked for."""

    def __init__(self, name: str) -> None:
        super().__init__(f"no term {name!r} in the record")


class TermFileError(Exception):
    """A file named as a term in a record that does not hold one; names its path."""


class TermMismatchError(Exception):
    """A term read back different from the one written; its file is as it was before."""


@dataclass(frozen=True)
class Term:
    """A term of the project: its name, what it means and the time it was added."""

    name: str
    meaning: str
    added: datetime


def make_term(name: str, meaning: str, added: datetime) -> Term:
    """The term of that name and meaning, added at that time.

    Raises TermError when the name is no lowercase words joined by `-` or reads as the id of an
    item, and EmptyPartError when the meaning is blank.
    """
    if ITEM_ID.fullmatch(name):
        raise TermError(f"{name!r} reads as the id of an item: a term name is no id")
    if not NAME.fullmatch(name):
        raise TermError(
            f"{name!r} is no term name: lowercase words of letters and digits joined by -"
        )
    return Term(name, said("meaning", meaning), added)


def is_term_name(text: str) -> bool:
    """True when the text is written as a term name: a term is shown by it, an item by its id."""
    return NAME.fullmatch(text) is not None and ITEM_ID.fullmatch(text) is None


class _TermFile(BaseModel):
    """What the file of a term holds."""

    model_config = ConfigDict(extra="forbid")

    name: str
    meaning: str
    added: datetime


def term_file(record: Path, name: str) -> Path:
    """The path of the file of the term of that name in the record."""
    return record / TERMS / f"{name}.toml"


def _read_file(path: Path) -> Term:
    """The term one file holds, built through its constructor.

    Raises TermFileError naming the path when the file holds no term.
    """
    try:
        held = _TermFile.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
        return make_term(held.name, held.meaning, held.added)
    except (tomllib.TOMLDecodeError, ValidationError, TermError, EmptyPartError) as error:
        raise TermFileError(f"{path} holds no term: {error}") from error


def read_term(record: Path, name: str) -> Term:
    """Adapter: the term of that name in the record, whole.

    Raises TermNotFoundError when the record holds no such term and TermFileError when its file
    does not hold a term of that name.
    """
    path = term_file(record, name)
    if not path.is_file():
        raise TermNotFoundError(name)
    held = _read_file(path)
    if held.name != name:
        raise TermFileError(f"{path} holds no term: it is named {held.name!r}, not {name!r}")
    return held


def read_term_names(record: Path) -> list[str]:
    """Adapter: the names of the terms in the record, as their files are named, in no order."""
    return [path.stem for path in (record / TERMS).glob("*.toml")]


def write_term(record: Path, term: Term) -> None:
    """Adapter: write the term as its one file in the record.

    It is written beside its file and read back before it replaces it. Raises TermMismatchError
    naming the file when the term read back differs; the file is then as it was before.
    """
    path = term_file(record, term.name)
    primitives = {"name": term.name, "meaning": term.meaning, "added": term.added}
    write_checked(
        path,
        primitives,
        lambda beside: _read_file(beside) == term,
        TermMismatchError(f"{path}: the term written reads back different"),
    )
