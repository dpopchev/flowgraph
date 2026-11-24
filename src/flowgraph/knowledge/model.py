"""A knowledge line: what a work item learned, kept on it in the order it was noted.

A line is never amended or removed. Its kind is a sum type: the finding, the decision and the
deviation. It may carry one mark, given when it is noted and never changed.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import said


@dataclass(frozen=True)
class Finding:
    """The kind of a line that states what the work learned."""


@dataclass(frozen=True)
class Decision:
    """The kind of a line that states what was decided."""


@dataclass(frozen=True)
class Deviation:
    """The kind of a line that states a change to what a started item was agreed to do."""


# The kind of knowledge a line holds.
KnowledgeKind = Finding | Decision | Deviation

# The three kinds there are.
FINDING = Finding()
DECISION = Decision()
DEVIATION = Deviation()


@dataclass(frozen=True)
class StandingMark:
    """The mark of a line that holds until a later line supersedes it."""


@dataclass(frozen=True)
class OpenMark:
    """The mark of a line not settled yet."""


@dataclass(frozen=True)
class NoMark:
    """The mark of a line noted with no mark."""


# The mark a line may carry.
Mark = StandingMark | OpenMark | NoMark

# The three marks there are.
STANDING = StandingMark()
OPEN = OpenMark()
UNMARKED = NoMark()


class MarkError(ValueError):
    """The word is no mark."""


@dataclass(frozen=True)
class KnowledgeLine:
    """One line of knowledge: its kind, its text, when it was noted and the terms it is about.

    It may govern files, each a path kept as written and never checked against the disk.
    """

    kind: KnowledgeKind
    text: str
    noted: datetime
    about: tuple[str, ...] = ()
    governs: tuple[str, ...] = ()
    mark: Mark = UNMARKED


@dataclass
class KnowledgeRow:
    """One line of knowledge as plain data, as a view reads it: the name of its kind first."""

    kind: str
    noted: datetime
    text: str
    about: list[str] = field(default_factory=list[str])
    governs: list[str] = field(default_factory=list[str])
    mark: str = ""


def kind_name(kind: KnowledgeKind) -> str:
    """The kind as the record writes it."""
    match kind:
        case Finding():
            return "finding"
        case Decision():
            return "decision"
        case Deviation():
            return "deviation"
        case _ as unreachable:
            assert_never(unreachable)


def make_mark(word: str | None) -> Mark:
    """The mark a word names: standing or open, or no mark for None.

    Raises MarkError for any other word.
    """
    match word:
        case None:
            return UNMARKED
        case "standing":
            return STANDING
        case "open":
            return OPEN
        case _:
            raise MarkError(f"{word!r} is no mark: standing or open")


def mark_name(mark: Mark) -> str:
    """The mark as the record writes it: standing, open or the empty text."""
    match mark:
        case StandingMark():
            return "standing"
        case OpenMark():
            return "open"
        case NoMark():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def mark_text(mark: str) -> str:
    """The mark as a view ends the text of a line with it; empty for none."""
    return f"  ({mark})" if mark else ""


def make_knowledge_line(
    kind: KnowledgeKind,
    text: str,
    noted: datetime,
    about: tuple[str, ...] = (),
    governs: tuple[str, ...] = (),
    mark: Mark = UNMARKED,
) -> KnowledgeLine:
    """The line of that kind and text, noted at that time, kept to the second, about those terms.

    It governs the files given and carries the mark given.

    Raises EmptyPartError naming the text when it is blank.
    """
    return KnowledgeLine(
        kind, said("text", text), noted.replace(microsecond=0), about, governs, mark
    )


def knowledge_row(line: KnowledgeLine) -> KnowledgeRow:
    """The line as the row a view reads."""
    return KnowledgeRow(
        kind_name(line.kind),
        line.noted,
        line.text,
        list(line.about),
        list(line.governs),
        mark_name(line.mark),
    )


def about_text(about: Sequence[str]) -> str:
    """The terms a line is about as a view ends the line with them; empty for none."""
    return f"  (about {', '.join(about)})" if about else ""


def governs_text(governs: Sequence[str]) -> str:
    """The files a line governs as a view ends the line with them; empty for none."""
    return f"  (governs {', '.join(governs)})" if governs else ""
