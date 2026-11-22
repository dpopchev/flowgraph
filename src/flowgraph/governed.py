"""The files a knowledge line governs: the paths a note keeps and the lines about reads for a path.

A path is kept from the top of the git work tree of the directory fgraph runs in, or as given
outside one. It is never checked against the disk: a governed file may be renamed or not yet
written.
"""

from collections.abc import Sequence
from pathlib import Path

from flowgraph.criterion import said
from flowgraph.development.commit import OpenGit, WorkTree
from flowgraph.knowledge_list import KnowledgeEntry, collected, newest_first
from flowgraph.record.store import Store


def placed(text: str, directory: Path, work_tree: WorkTree | None) -> str | None:
    """The path of the text from the directory, as a path from the top of the work tree.

    None outside a work tree and for a path that leads out of it.
    """
    if work_tree is None:
        return None
    try:
        return (directory / text).resolve().relative_to(work_tree.path.resolve()).as_posix()
    except ValueError:
        return None


def governs_asked(
    paths: Sequence[str] | None, directory: Path, open_git: OpenGit
) -> tuple[str, ...]:
    """The files a command asks a line to govern, each once, in order; empty when it names none.

    Each is a path from the top of the git work tree of the directory, or as given outside one.
    Raises EmptyPartError for a blank path; nothing is written.
    """
    work_tree = open_git(directory)
    return tuple(
        dict.fromkeys(
            placed(said("governs", path), directory, work_tree) or path for path in paths or ()
        )
    )


def governing(text: str, directory: Path, store: Store, open_git: OpenGit) -> list[KnowledgeEntry]:
    """The lines that govern the file the text names, as given or from the top, newest first."""
    named = {text, placed(text, directory, open_git(directory))}
    return [
        entry for entry in newest_first(collected(store), None) if named.intersection(entry.governs)
    ]


def governed_text(entries: Sequence[KnowledgeEntry]) -> str:
    """The lines under their heading, Governed by, each with its kind, day, item and text.

    Empty for none.
    """
    if not entries:
        return ""
    return "Governed by\n" + "".join(
        f"  {entry.kind}  {entry.noted.date().isoformat()}  {entry.item}  {entry.text}\n"
        for entry in entries
    )
