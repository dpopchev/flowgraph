"""The JSON document of the knowledge lines of a record: a second formatter beside the text.

No fact is computed here: the lines come in the order given, a key that holds nothing is null and
a list that holds nothing is empty. The keys are sorted and the text ends with a newline, so two
runs on one record print the same bytes.
"""

import json
from collections.abc import Iterable
from typing import Any

from flowgraph.knowledge.list import KnowledgeEntry, listed_knowledge, show_knowledge
from flowgraph.record.store import Store

# The two formats of knowledge; the first is the default.
TEXT = "text"
JSON = "json"

type Part = dict[str, Any]


class KnowledgeFormatError(ValueError):
    """A format of knowledge that is none there is."""


def chosen_knowledge_format(format_: str) -> str:
    """The format of knowledge asked for.

    Raises KnowledgeFormatError naming the word and the two formats when it is neither.
    """
    if format_ not in (TEXT, JSON):
        raise KnowledgeFormatError(
            f"--format {format_!r} is not {TEXT} or {JSON}, the two formats of knowledge"
        )
    return format_


def _line(entry: KnowledgeEntry) -> Part:
    """A knowledge line with its nine fields; a mark or a ref it has none of is null."""
    return {
        "about": list(entry.about),
        "governs": list(entry.governs),
        "item": entry.item,
        "kind": entry.kind,
        "mark": entry.mark or None,
        "noted": entry.noted.isoformat(),
        "ref": entry.ref or None,
        "supersedes": list(entry.supersedes),
        "text": entry.text,
    }


def knowledge_json(entries: Iterable[KnowledgeEntry]) -> str:
    """The lines as one JSON document, {lines: [...]}, each line with its nine fields."""
    document = {"lines": [_line(entry) for entry in entries]}
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def knowledge_output(
    format_: str,
    kind: str | None,
    about: str | None,
    store: Store,
    search: str | None = None,
    live: bool = False,
) -> str:
    """The output of fgraph knowledge in the format asked for: the same lines in either format.

    Raises KnowledgeFormatError before the record is read when the format is neither, and the
    refusals of listed_knowledge; nothing is written.
    """
    chosen = chosen_knowledge_format(format_)
    if chosen == JSON:
        return knowledge_json(listed_knowledge(kind, about, store, search, live))
    return show_knowledge(kind, about, store, search, live)
