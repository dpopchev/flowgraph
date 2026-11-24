"""A term of the project: a node of the record with no flow, kept as one file, `terms/gate.toml`.

A term is the name of a thing the project talks about and what it means. Its name is its id:
lowercase words of letters and digits joined by `-`, never one that reads as the id of an item.
It is in no bucket and no queue, since nothing is done to it: it is added and then it stands.
A term is related to others by a closed set of kinds, `is-a` and `part-of`; a relation is kept in
the file of the term that names it, the first, and the other side is read from the record.
"""

import re
import tomllib
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from flowgraph.criterion import EmptyPartError, said
from flowgraph.item import HeldTime, NoOffsetError, write_checked

# The directory of every term inside a record, one file per term, named by its name.
TERMS = "terms"

# A name: words of lowercase letters and digits, joined by one dash.
NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

# What reads as the id of an item: letters, a dash and a number, as F-0001 or S-0001.
ITEM_ID = re.compile(r"[A-Za-z]+-\d+")


# The kinds of relation between two terms, held once: a term is a kind of another or part of it.
IS_A = "is-a"
PART_OF = "part-of"
KINDS = (IS_A, PART_OF)


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
    """A term of the project: its name, what it means, the time it was added and its relations.

    `is_a` names the terms it is a kind of and `part_of` those it is part of, each once, in order.
    """

    name: str
    meaning: str
    added: datetime
    is_a: tuple[str, ...] = ()
    part_of: tuple[str, ...] = ()


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


def named_by(term: Term, kind: str) -> tuple[str, ...]:
    """The names of the terms the term is related to by that kind, in order of their relating."""
    return term.is_a if kind == IS_A else term.part_of


def relate(term: Term, kind: str, other: str) -> Term:
    """The term related to the other by that kind, the rest as it was.

    Raises TermError when the kind is outside the set, when the term is the other and when it is
    related so already.
    """
    if kind not in KINDS:
        raise TermError(f"{kind!r} is no kind of relation: {' or '.join(KINDS)}")
    if term.name == other:
        raise TermError(f"{term.name} cannot be {kind} itself")
    held = named_by(term, kind)
    if other in held:
        raise TermError(f"{term.name} is {kind} {other} already")
    return replace(term, **{kind.replace("-", "_"): (*held, other)})


def is_term_name(text: str) -> bool:
    """True when the text is written as a term name: a term is shown by it, an item by its id."""
    return NAME.fullmatch(text) is not None and ITEM_ID.fullmatch(text) is None


class _TermFile(BaseModel):
    """What the file of a term holds."""

    model_config = ConfigDict(extra="forbid")

    name: str
    meaning: str
    added: HeldTime
    is_a: list[str] = []
    part_of: list[str] = []


def term_file(record: Path, name: str) -> Path:
    """The path of the file of the term of that name in the record."""
    return record / TERMS / f"{name}.toml"


def _read_file(path: Path) -> Term:
    """The term one file holds, built through its constructor.

    Raises TermFileError naming the path when the file holds no term; a time with no offset is
    refused so.
    """
    try:
        held = _TermFile.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
        made = make_term(held.name, held.meaning, held.added)
        return replace(made, is_a=tuple(held.is_a), part_of=tuple(held.part_of))
    except (
        tomllib.TOMLDecodeError,
        ValidationError,
        TermError,
        EmptyPartError,
        NoOffsetError,
    ) as error:
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
    primitives: dict[str, object] = {
        "name": term.name,
        "meaning": term.meaning,
        "added": term.added,
    }
    if term.is_a:
        primitives["is_a"] = list(term.is_a)
    if term.part_of:
        primitives["part_of"] = list(term.part_of)
    write_checked(
        path,
        primitives,
        lambda beside: _read_file(beside) == term,
        TermMismatchError(f"{path}: the term written reads back different"),
    )
