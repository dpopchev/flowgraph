"""The worktrees of one repository: the Task ids their records hold together.

A Task id is unique across the record, and a started work item is written in a worktree of its
own. So the next Task id is one above the highest in the record of every worktree: main and a
worktree hand out no id twice. It covers the worktrees of one repository, not two clones.
"""

from dataclasses import replace
from pathlib import Path

from flowgraph.commit import OpenGit
from flowgraph.store import OpenStore, Store


def across_worktrees(store: Store, record: Path, open_git: OpenGit, open_store: OpenStore) -> Store:
    """The store whose Task ids are those of the record of every worktree of the repository.

    The record of another worktree is the directory at the same path inside it as the record has
    inside its own work tree, opened by open_store. Outside a git work tree the ids are those of
    the record alone. The worktrees are asked for only when the ids are.
    """

    def find_task_ids() -> list[str]:
        work_tree = open_git(record)
        if work_tree is None:
            return store.find_task_ids()
        top = work_tree.path.resolve()
        inside = record.resolve().relative_to(top)
        others = [path / inside for path in work_tree.find_worktrees() if path.resolve() != top]
        elsewhere = [task for other in others for task in open_store(other).find_task_ids()]
        return [*store.find_task_ids(), *elsewhere]

    return replace(store, find_task_ids=find_task_ids)
