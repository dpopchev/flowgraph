"""The check of a Task, run in the worktree of its work item before the Task completes."""

from pathlib import Path

from flowgraph.development.commit import OpenGit
from flowgraph.development.gate import RunGate
from flowgraph.development.scope import worktree_of_item
from flowgraph.development.task_check import check_task_passes
from flowgraph.item.moves import load_holder
from flowgraph.record.store import Store
from flowgraph.task import StartedTask, TaskIdError, TaskNotFoundError, parse_task_id, task_id_text


def check_task_run(
    item: str, store: Store, record: Path, open_git: OpenGit, cwd: Path, run_check: RunGate
) -> None:
    """Run the check of the started Task of that id, in the worktree of its work item.

    The worktree is the one the branch of the work item is checked out in, else cwd. An id that
    is no Task's, a Task no item holds and a Task not started run nothing: the complete refuses
    them. Raises TaskCheckError when the check exits with another status than 0.
    """
    try:
        task_id = parse_task_id(item)
        holder = load_holder(store)(task_id)
    except TaskIdError, TaskNotFoundError:
        return
    for task in holder.tasks:
        if task.id == task_id and isinstance(task, StartedTask):
            where = worktree_of_item(record, open_git, holder.id) or cwd
            check_task_passes(task_id_text(task_id), task.check, where, run_check)
