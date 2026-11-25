"""The JSON document of fgraph about, a second formatter of the links beside its text (S-0156).

It formats the links of `about/links.py` as `about/text.py` words them. No fact is computed here
but the kind of a work item, read from the prefix of its id. Every relation is present and empty
as [], where the text leaves out a heading with nothing; an empty text is null. The keys are
sorted and the text ends with a newline, so two runs on one record print the same bytes.
"""

import json
from typing import Any, assert_never

from flowgraph.about.links import (
    About,
    FileLinks,
    ItemLinks,
    Linked,
    TermLinks,
    Touching,
)
from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.knowledge.model import KnowledgeRow
from flowgraph.record.store import KINDS

# The two formats of about; the first is the default.
TEXT = "text"
JSON = "json"

type Part = dict[str, Any]


class AboutFormatError(ValueError):
    """A format of about that is none there is."""


def chosen_about_format(format_: str) -> str:
    """The format of about asked for.

    Raises AboutFormatError naming the word and the two formats when it is neither.
    """
    if format_ not in (TEXT, JSON):
        raise AboutFormatError(
            f"--format {format_!r} is not {TEXT} or {JSON}, the two formats of about"
        )
    return format_


def _linked(each: Linked) -> Part:
    """A work item or a Feature linked, with its bucket and its title."""
    return {"bucket": each.bucket, "id": each.id, "title": each.title}


def _row(row: KnowledgeRow) -> Part:
    """A knowledge line of an item; an empty mark is null."""
    return {
        "about": list(row.about),
        "governs": list(row.governs),
        "kind": row.kind,
        "mark": row.mark or None,
        "noted": row.noted.isoformat(),
        "supersedes": list(row.supersedes),
        "text": row.text,
    }


def _entry(entry: KnowledgeEntry) -> Part:
    """A knowledge line with the id of its item: its nine keys; an empty mark or ref is null."""
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


def _item(links: ItemLinks) -> Part:
    """A work item or a Feature: its id, kind and title, each relation by its key."""
    kinds = {kind.prefix: kind.noun.lower() for kind in KINDS}
    prefix = links.id.partition("-")[0]
    return {
        "id": links.id,
        "kind": "feature" if prefix == "F" else kinds[prefix],
        "title": links.title,
        **{
            heading.replace(" ", "_"): [_linked(each) for each in held]
            for heading, held in links.links.items()
        },
        "terms": [{"meaning": term.meaning, "name": term.name} for term in links.terms],
        "knowledge": [_row(row) for row in links.knowledge],
    }


def _term(links: TermLinks) -> Part:
    """A term: its head, the items about it and its lines, each with the term it was reached by."""
    return {
        "name": links.name,
        "kind": "term",
        "meaning": links.meaning,
        "added": links.added.isoformat(),
        "is_a": list(links.is_a),
        "part_of": list(links.part_of),
        "kinds": links.kinds,
        "parts": links.parts,
        "items": [{"id": each.id, "via": each.via or None} for each in links.items],
        "knowledge": [{**_entry(line.entry), "via": line.via or None} for line in links.knowledge],
    }


def _touching(each: Touching) -> Part:
    """An item that touched a file; its commit is null when only a Task of it did."""
    return {
        "commit": each.commit or None,
        "id": each.id,
        "tasks": [
            {"commit": task.commit, "id": task.id, "title": task.title} for task in each.tasks
        ],
        "title": each.title,
    }


def _file(links: FileLinks) -> Part:
    """A file: its path as given, the lines that govern it and the items that touched it."""
    return {
        "path": links.path,
        "kind": "file",
        "governed_by": [_entry(entry) for entry in links.governed_by],
        "touched_by": [_touching(each) for each in links.touched_by],
    }


def about_json(links: About) -> str:
    """The links as a JSON document: an item, a term or a file, by the keys of its contract."""
    match links:
        case ItemLinks():
            document = _item(links)
        case TermLinks():
            document = _term(links)
        case FileLinks():
            document = _file(links)
        case _ as unreachable:
            assert_never(unreachable)
    return json.dumps(document, indent=2, sort_keys=True) + "\n"
