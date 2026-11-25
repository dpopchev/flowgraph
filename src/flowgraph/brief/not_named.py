"""The files changed in a worktree, before the commit of a Task, that its brief does not name.

Read by the rule fgraph complete holds the commit of the Task to, files_not_named of
flowgraph.development.named_files (S-0142), over the same three texts: the title, the expected
output and the description of the started Task of the work item. A file listed is one the
complete refuses once it is committed. It reads, never writes (S-0153).
"""

import json
from collections.abc import Sequence
from pathlib import Path

from flowgraph.brief.document import JSON
from flowgraph.brief.model import Brief
from flowgraph.development.commit import OpenGit
from flowgraph.development.named_files import files_not_named
from flowgraph.work_item import STARTED

NO_STARTED_TASK = "{id} has no started Task: --not-named reads the brief of the Task started"
NO_WORK_TREE = "{id} has no files changed to read: the record is not inside a git work tree"


class NotNamedError(ValueError):
    """A work item with no started Task, or a record outside a git work tree."""


def not_named_of(brief: Brief, record: Path, open_git: OpenGit) -> list[str]:
    """The files changed and not committed that the brief of the started Task does not name.

    Read from the worktree of the brief, else from the work tree of the record; the files under
    the directory of the record are never listed. Raises NotNamedError when the work item has no
    started Task, before git is asked, and when the record is not inside a git work tree.
    """
    task = next((task for task in brief.detail.tasks if task.state == STARTED), None)
    if task is None:
        raise NotNamedError(NO_STARTED_TASK.format(id=brief.detail.id))
    home = open_git(record)
    if home is None:
        raise NotNamedError(NO_WORK_TREE.format(id=brief.detail.id))
    inside = f"{record.resolve().relative_to(home.path.resolve()).as_posix()}/"
    work_tree = (open_git(brief.worktree) if brief.worktree else None) or home
    files = [file for file in work_tree.uncommitted_files() if not file.startswith(inside)]
    return files_not_named(files, (task.title, task.expected_output, task.description))


def not_named_document(files: Sequence[str], format_: str) -> str:
    """The files each on its line, empty for none, or as a JSON list when the format is json."""
    if format_ == JSON:
        return json.dumps(list(files)) + "\n"
    return "".join(f"{file}\n" for file in files)
