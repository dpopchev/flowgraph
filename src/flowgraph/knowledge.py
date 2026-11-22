"""A knowledge line: what a work item learned, kept on it in the order it was noted.

A line is never amended or removed. Its kind is a sum type: the finding is the one kind so far.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import said


@dataclass(frozen=True)
class Finding:
    """The kind of a line that states what the work learned."""


# The kind of knowledge a line holds.
KnowledgeKind = Finding

# The finding, as the one kind there is.
FINDING = Finding()


@dataclass(frozen=True)
class KnowledgeLine:
    """One line of knowledge: its kind, its text and the time it was noted."""

    kind: KnowledgeKind
    text: str
    noted: datetime


@dataclass
class KnowledgeRow:
    """One line of knowledge as plain data, as a view reads it: the name of its kind first."""

    kind: str
    noted: datetime
    text: str


def kind_name(kind: KnowledgeKind) -> str:
    """The kind as the record writes it."""
    match kind:
        case Finding():
            return "finding"
        case _ as unreachable:
            assert_never(unreachable)


def make_knowledge_line(kind: KnowledgeKind, text: str, noted: datetime) -> KnowledgeLine:
    """The line of that kind and text, noted at that time, kept to the second.

    Raises EmptyPartError naming the text when it is blank.
    """
    return KnowledgeLine(kind, said("text", text), noted.replace(microsecond=0))


def knowledge_row(line: KnowledgeLine) -> KnowledgeRow:
    """The line as the row a view reads."""
    return KnowledgeRow(kind_name(line.kind), line.noted, line.text)
