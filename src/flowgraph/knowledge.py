"""A knowledge line: what a work item learned, kept on it in the order it was noted.

A line is never amended or removed. Its kind is a sum type: the finding, the decision and the
deviation.
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
class KnowledgeLine:
    """One line of knowledge: its kind, its text, when it was noted and the terms it is about."""

    kind: KnowledgeKind
    text: str
    noted: datetime
    about: tuple[str, ...] = ()


@dataclass
class KnowledgeRow:
    """One line of knowledge as plain data, as a view reads it: the name of its kind first."""

    kind: str
    noted: datetime
    text: str
    about: list[str] = field(default_factory=list[str])


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


def make_knowledge_line(
    kind: KnowledgeKind, text: str, noted: datetime, about: tuple[str, ...] = ()
) -> KnowledgeLine:
    """The line of that kind and text, noted at that time, kept to the second, about those terms.

    Raises EmptyPartError naming the text when it is blank.
    """
    return KnowledgeLine(kind, said("text", text), noted.replace(microsecond=0), about)


def knowledge_row(line: KnowledgeLine) -> KnowledgeRow:
    """The line as the row a view reads."""
    return KnowledgeRow(kind_name(line.kind), line.noted, line.text, list(line.about))


def about_text(about: Sequence[str]) -> str:
    """The terms a line is about as a view ends the line with them; empty for none."""
    return f"  (about {', '.join(about)})" if about else ""
