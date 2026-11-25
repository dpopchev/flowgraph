"""The completed items whose commits touched a file, listed: a view read from git, never stored.

A file is a derived node of the record. The record names the commit each completed work item
and each completed Task was completed at; git names the files a commit changed.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from flowgraph.about.links import FileLinks, TouchedTask, Touching
from flowgraph.development.commit import OpenGit
from flowgraph.item.id import ItemIdError
from flowgraph.knowledge.governed import governing, placed
from flowgraph.record.store import Store
from flowgraph.status import COMPLETED, rows_by_id
from flowgraph.work_item import WorkItemRow

# Whether a commit changed the file asked about.
Touched = Callable[[str], bool]

# The time of a completed work item the record gives none for: before every other.
_BEFORE_ALL = datetime.min.replace(tzinfo=UTC)


def is_file_here(text: str, directory: Path) -> bool:
    """True when the text names a file, from the directory fgraph runs in."""
    return (directory / text).is_file()


def is_governed(text: str, directory: Path, store: Store, open_git: OpenGit) -> bool:
    """True when a line of the record governs the file the text names, on the disk or not."""
    return bool(governing(text, directory, store, open_git))


def file_links(text: str, directory: Path, store: Store, open_git: OpenGit) -> FileLinks:
    """The lines that govern the file, then the completed items whose commit changed it.

    The path is taken from the directory fgraph runs in. The lines come first, newest first. A
    work item has its commit when its own commit changed the file, none when only a Task of it
    did, and a Task is held under its work item. Outside a git work tree, or for a path outside
    the one of the directory, the lines that govern it alone are held. Raises ItemIdError there
    when no line governs it.
    """
    work_tree = open_git(directory)
    governed = governing(text, directory, store, open_git)
    file = placed(text, directory, work_tree)
    if work_tree is None or file is None:
        if governed:
            return FileLinks(text, governed, [])
        if work_tree is None:
            raise ItemIdError(
                f"{text!r} is a file: the answer for a file is read from git, and {directory}"
                " is inside no git work tree"
            )
        raise ItemIdError(
            f"{text!r} is outside the git work tree {work_tree.path.resolve()}: the answer for a"
            " file is read from git"
        )

    def touched(commit: str) -> bool:
        return bool(commit) and file in (work_tree.changed_files(commit) or [])

    done = [row for row in rows_by_id(store).values() if row.state == COMPLETED]
    found = (_touching(row, touched) for row in sorted(done, key=_completed, reverse=True))
    return FileLinks(text, governed, [each for each in found if each])


def _completed(row: WorkItemRow) -> datetime:
    """The time the work item was completed."""
    return row.completed or _BEFORE_ALL


def _touching(row: WorkItemRow, touched: Touched) -> Touching | None:
    """The work item as the file touched it: its own commit, then each Task of it that did."""
    own = touched(row.commit)
    tasks = [
        TouchedTask(task.id, task.commit, task.title) for task in row.tasks if touched(task.commit)
    ]
    if not own and not tasks:
        return None
    return Touching(row.id, row.commit if own else "", row.title, tasks)
