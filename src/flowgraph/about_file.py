"""The completed items whose commits touched a file, listed: a view read from git, never stored.

A file is a derived node of the record. The record names the commit each completed work item
and each completed Task was completed at; git names the files a commit changed.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from flowgraph.commit import OpenGit
from flowgraph.item_id import ItemIdError
from flowgraph.status import COMPLETED, rows_by_id
from flowgraph.store import Store
from flowgraph.work_item import WorkItemRow

# Whether a commit changed the file asked about.
Touched = Callable[[str], bool]

# The time of a completed work item the record gives none for: before every other.
_BEFORE_ALL = datetime.min.replace(tzinfo=UTC)


def is_file_here(text: str, directory: Path) -> bool:
    """True when the text names a file, from the directory fgraph runs in."""
    return (directory / text).is_file()


def about_file(text: str, directory: Path, store: Store, open_git: OpenGit) -> str:
    """The completed work items and Tasks whose commit changed the file, newest first.

    The path is taken from the directory fgraph runs in. A work item is listed with its commit
    when its own commit changed the file, with none when only a Task of it did, and a Task is
    listed under its work item. A file no commit of the record touched is said so in one line.
    Raises ItemIdError outside a git work tree, or for a path outside the one of the directory.
    """
    work_tree = open_git(directory)
    if work_tree is None:
        raise ItemIdError(
            f"{text!r} is a file: the answer for a file is read from git, and {directory}"
            " is inside no git work tree"
        )
    top = work_tree.path.resolve()
    try:
        file = (directory / text).resolve().relative_to(top).as_posix()
    except ValueError as error:
        raise ItemIdError(
            f"{text!r} is outside the git work tree {top}: the answer for a file is read from git"
        ) from error

    def touched(commit: str) -> bool:
        return bool(commit) and file in (work_tree.changed_files(commit) or [])

    done = [row for row in rows_by_id(store).values() if row.state == COMPLETED]
    lines = "".join(_lines(row, touched) for row in sorted(done, key=_completed, reverse=True))
    return lines or f"no commit of the record touched {text}\n"


def _completed(row: WorkItemRow) -> datetime:
    """The time the work item was completed."""
    return row.completed or _BEFORE_ALL


def _lines(row: WorkItemRow, touched: Touched) -> str:
    """The lines of a work item the file touched: its own, then each Task of it that did."""
    own = touched(row.commit)
    tasks = [task for task in row.tasks if touched(task.commit)]
    if not own and not tasks:
        return ""
    head = f"{row.id}  {row.commit if own else '-'}  {row.title}\n"
    return head + "".join(f"  {task.id}  {task.commit}  {task.title}\n" for task in tasks)
