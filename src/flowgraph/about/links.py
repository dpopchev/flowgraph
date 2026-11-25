"""The links fgraph about lists, as plain data a view reads from the record and git (S-0156).

Data alone: `about/view.py` and `about/file.py` read them, `about/text.py` words them.
"""

from dataclasses import dataclass, field
from datetime import datetime

from flowgraph.brief.model import TermLine
from flowgraph.knowledge import KnowledgeRow
from flowgraph.knowledge.list import KnowledgeEntry


@dataclass(frozen=True)
class Linked:
    """A work item or a Feature linked: its id, its bucket and its title, one line of the text."""

    id: str
    bucket: str
    title: str


@dataclass
class ItemLinks:
    """The links of a work item or a Feature, under the heading the text lists them by.

    The headings come in the order of the text, every one present, empty or not: feature,
    depends on, depended on by, filed during, filed here, supersedes, superseded by, amends and
    amended by for a work item; work items for a Feature.
    """

    id: str
    title: str
    links: dict[str, list[Linked]]
    terms: list[TermLine]
    knowledge: list[KnowledgeRow]


@dataclass(frozen=True)
class Reached:
    """A work item or a Feature about a term, with the term under it it was reached through.

    `via` is empty for the term itself.
    """

    id: str
    via: str


@dataclass(frozen=True)
class ReachedLine:
    """A knowledge line about a term, with the term under it it was reached through.

    `via` is empty for the term itself.
    """

    entry: KnowledgeEntry
    via: str


@dataclass
class TermLinks:
    """A term with its head and what is about it and about every term under it."""

    name: str
    meaning: str
    added: datetime
    is_a: tuple[str, ...]
    part_of: tuple[str, ...]
    kinds: list[str]
    parts: list[str]
    items: list[Reached] = field(default_factory=list[Reached])
    knowledge: list[ReachedLine] = field(default_factory=list[ReachedLine])


@dataclass(frozen=True)
class TouchedTask:
    """A completed Task whose commit changed a file."""

    id: str
    commit: str
    title: str


@dataclass
class Touching:
    """A completed work item that touched a file, with the Tasks of it that did.

    `commit` is empty when a Task of it alone touched the file, which the text writes as `-`.
    """

    id: str
    commit: str
    title: str
    tasks: list[TouchedTask]


@dataclass
class FileLinks:
    """A file: the lines that govern it and the completed items whose commits touched it.

    `path` is the text as given.
    """

    path: str
    governed_by: list[KnowledgeEntry]
    touched_by: list[Touching]


# What fgraph about reads: the links of an item, of a term or of a file.
type About = ItemLinks | TermLinks | FileLinks
