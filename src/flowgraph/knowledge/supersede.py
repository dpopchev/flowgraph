"""The lines a line supersedes, as a note names them and as a view reads them back.

The supersede is kept on the later line, so the earlier is never rewritten and the other side is
read from the record.
"""

from collections.abc import Sequence
from dataclasses import replace

from flowgraph.item.id import id_spelled
from flowgraph.knowledge.list import collected, superseded_by
from flowgraph.knowledge.model import KnowledgeRow, line_ref
from flowgraph.record.store import Store


class LineRefError(ValueError):
    """A ref a note supersedes that is the ref of no knowledge line of the record."""


def supersedes_asked(texts: Sequence[str] | None, store: Store) -> tuple[str, ...]:
    """The refs of the lines a note supersedes, each once, in the order given.

    None names none, and the store is not read. Each ref is read in any spelling of its id, as
    s1#2 for S-0001#2. Raises LineRefError with the text as typed when it is the ref of no line
    of the record: a text with no #, an id the record does not hold, a place past the last line,
    a Task or the decision of a Spike; nothing is written.
    """
    if texts is None:
        return ()
    held = {entry.ref for entry in collected(store) if entry.ref}
    refs: list[str] = []
    for text in texts:
        item, mark, place = text.rpartition("#")
        ref = f"{id_spelled(item)}{mark}{place}"
        if ref not in held:
            raise LineRefError(
                f"--supersedes names {text}, which is no knowledge line of the record: "
                "fgraph knowledge lists each line with its ref"
            )
        refs.append(ref)
    return tuple(dict.fromkeys(refs))


def superseded_rows(item: str, rows: Sequence[KnowledgeRow], store: Store) -> list[KnowledgeRow]:
    """The rows of the item of that id, each with the refs of the lines that supersede it.

    The lines that supersede one are read from the whole record; with no row it is not read.
    """
    if not rows:
        return list(rows)
    named = superseded_by(collected(store))
    return [
        replace(row, superseded_by=named.get(line_ref(item, place), []))
        for place, row in enumerate(rows, start=1)
    ]
