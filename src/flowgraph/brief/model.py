"""The brief of a work item as plain data, and which lines govern a path its Tasks name."""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.knowledge.model import KnowledgeRow
from flowgraph.task.model import TaskRow
from flowgraph.work_item.views import WorkItemDetail


@dataclass(frozen=True)
class TermLine:
    """A term the work item, its Feature or a line that governs it is about, with its meaning."""

    name: str
    meaning: str


@dataclass(frozen=True)
class FeatureBrief:
    """The Feature of a work item: its id, the bucket it is listed in, its title and its lines."""

    id: str
    bucket: str
    title: str
    description: str
    knowledge: tuple[KnowledgeRow, ...]


@dataclass(frozen=True)
class Brief:
    """A work item whole with what a coordinator hands an agent beside it.

    The branch and the worktree git holds for it, none when it has none; its Feature, none for a
    work item that stands alone; the live lines of the record that govern a path its Tasks name,
    those no later line supersedes, newest first; and the terms it, its Feature or one of those
    lines is about, each once.
    """

    detail: WorkItemDetail
    branch: str | None
    worktree: Path | None
    feature: FeatureBrief | None
    governed_by: tuple[KnowledgeEntry, ...]
    terms: tuple[TermLine, ...]


def governing(entries: Iterable[KnowledgeEntry], tasks: Sequence[TaskRow]) -> list[KnowledgeEntry]:
    """The entries that govern a path a Task names, in the order given.

    A path is named when it stands as a whole path in the expected output or the description of
    a Task: no letter, digit, slash, dot, underscore or hyphen before it, and no letter, digit,
    slash, underscore or hyphen after it.
    """
    texts = [part for task in tasks for part in (task.expected_output, task.description)]
    return [entry for entry in entries if any(_named(path, texts) for path in entry.governs)]


def _named(path: str, texts: Iterable[str]) -> bool:
    """True when one of the texts names the path as a whole path."""
    whole = re.compile(rf"(?<![\w/.-]){re.escape(path)}(?![\w/-])")
    return any(whole.search(text) for text in texts)
