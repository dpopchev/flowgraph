"""fgraph commit, the commit of the work of a started Task: the files changed that its brief names.

The files changed and not committed in the work tree of the record, each named by the brief of
the Task -- its title, its expected output and its description -- by files_not_named, the rule
fgraph complete holds that commit to (S-0142) and fgraph brief --not-named lists by (S-0153). It
writes no file of the record and does not complete the Task (S-0161).
"""

from pathlib import Path

from flowgraph.criterion import said
from flowgraph.development.commit import OpenGit, Said
from flowgraph.development.named_files import files_not_named, outside_record
from flowgraph.item.moves import load_holder
from flowgraph.record.store import Store
from flowgraph.task import StartedTask, parse_task_id, task_id_text
from flowgraph.work_item import BlockedWorkItem, work_item_id_text

# The refusal of a commit of a Task that is not started.
NOT_STARTED = "{task} is not started: fgraph commit commits the work of the Task started"
# The refusal of a commit of a record outside a git work tree.
NO_WORK_TREE = "{task} has no files to commit: the record is not inside a git work tree"
# The refusal of a commit when no file is changed in the work tree.
NOTHING = "{task} has nothing to commit: no file is changed in {top}"
# The refusal of a commit of a file the brief does not name; the files joined by a comma.
NOT_NAMED = (
    "{task} cannot commit: its brief does not name {files} -- nothing is committed; "
    "take each back or have the brief name it"
)


class CommitTaskError(ValueError):
    """A commit refused: a Task not started, no work tree, nothing changed or a file not named."""


def commit_task(item: str, message: str, store: Store, record: Path, open_git: OpenGit) -> Said:
    """Commit the files changed that the brief of the started Task names; say the sha."""
    task_id = parse_task_id(item)
    text = said("message", message)
    holder = load_holder(store)(task_id)
    task = None
    if not isinstance(holder, BlockedWorkItem):
        task = next(
            (t for t in holder.tasks if t.id == task_id and isinstance(t, StartedTask)), None
        )
    name = task_id_text(task_id)
    if task is None:
        raise CommitTaskError(NOT_STARTED.format(task=name))
    work_tree = open_git(record)
    if work_tree is None:
        raise CommitTaskError(NO_WORK_TREE.format(task=name))
    files = outside_record(work_tree.uncommitted_files(), record, work_tree.path)
    if not files:
        raise CommitTaskError(NOTHING.format(task=name, top=work_tree.path))
    unnamed = files_not_named(files, (task.title, task.expected_output, task.description))
    if unnamed:
        raise CommitTaskError(NOT_NAMED.format(task=name, files=", ".join(unnamed)))
    ids = f"{work_item_id_text(holder.id)}, {name}"
    sha = work_tree.commit_files([Path(file) for file in files], f"{text} ({ids})")
    return Said(f"committed {name} of {work_item_id_text(holder.id)} at {sha}\n")
