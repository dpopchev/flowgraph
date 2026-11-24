"""The check of the commit a completion is given: with the development on, the repository holds it.

The commit of a completion is the evidence of the development, so with it on the repository of the
record must hold it. With the development on, the commit of a completion is asked of git, and a
sha git does not know is refused before anything is written or any check of the Task runs. With
the development off, or outside a git work tree, the commit is kept as given.
"""

from pathlib import Path
from typing import assert_never

from flowgraph.criterion import CommitError, make_commit
from flowgraph.development.commit import OpenGit
from flowgraph.item.commands import ItemIdError, parse_item_id
from flowgraph.record import Config
from flowgraph.task import TaskId, task_id_text
from flowgraph.work_item import WorkItemId, work_item_id_text

# The refusal of a completion given a commit the repository does not hold, with the id and the sha.
NOT_HELD = "{id} cannot complete: the repository holds no commit {sha}"


class CommitNotHeldError(ValueError):
    """A completion given a commit the repository does not hold; names the item and the sha."""


def check_commit_held(
    item: str, sha: str | None, record: Path, open_git: OpenGit, config: Config
) -> None:
    """Raise CommitNotHeldError when the commit given is not held by the repository of the record.

    Nothing is asked of git unless the development is on and a commit is given. A Feature, a
    text that is no id and a text that is no sha are left to the complete, which refuses each in
    its own words; a record outside a git work tree is not asked. The sha is asked as given.
    """
    if not config.development.enabled or sha is None:
        return
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    try:
        make_commit(sha)
    except CommitError:
        return
    work_tree = open_git(record)
    if work_tree is None:
        return
    if work_tree.changed_files(sha) is None:
        raise CommitNotHeldError(NOT_HELD.format(id=_id_text(item_id), sha=sha))


def _id_text(item_id: TaskId | WorkItemId) -> str:
    """The text of the id of a Task or of a work item."""
    match item_id:
        case TaskId():
            return task_id_text(item_id)
        case WorkItemId():
            return work_item_id_text(item_id)
        case _ as unreachable:
            assert_never(unreachable)
