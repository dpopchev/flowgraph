"""The files a commit may change: those the brief of a Task names.

The brief of a Task -- its title, its expected output and its description -- names the files its
commit may change (S-0142, the scope rule 1 of board 1); the rule reads words, not intent.
"""

import re
from collections.abc import Iterable
from pathlib import Path

from flowgraph.criterion import CommitError, make_commit
from flowgraph.development.commit import OpenGit
from flowgraph.item.moves import load_holder
from flowgraph.record import Config
from flowgraph.record.store import Store
from flowgraph.task import StartedTask, TaskIdError, TaskNotFoundError, parse_task_id, task_id_text
from flowgraph.work_item import BlockedWorkItem

# The refusal of a completion at a commit that changed a file the brief does not name.
NOT_NAMED = "{id} cannot complete: the commit {sha} changed what its brief does not name: {files}"


class FilesNotNamedError(ValueError):
    """A completion at a commit that changed a file its brief does not name; lists each file."""


_OPENING = "([{<\"'`"
_CLOSING = ")]}>\"'`,;:.!?"
_LINE_OR_TEST = re.compile(r":(?=[0-9:])")


def path_words(text: str) -> frozenset[str]:
    """The words of the text that may name a path, cleaned of the punctuation around them.

    The brackets and quotes at the start of a word and the punctuation at its end are stripped,
    one leading ./ is dropped, and a line number or a test name after a colon is cut, so
    src/a.py:12 and src/a.py::test_x are read as src/a.py.
    """
    words = (word.lstrip(_OPENING).rstrip(_CLOSING) for word in text.split())
    cleaned = (_LINE_OR_TEST.split(word.removeprefix("./"), maxsplit=1)[0] for word in words)
    return frozenset(word for word in cleaned if word)


def files_not_named(changed: Iterable[str], brief: Iterable[str]) -> list[str]:
    """The files, in the order given, that no text of the brief names.

    A file, as git writes it, is named when a word of a text equals it, or ends in / and starts it.
    """
    words = frozenset().union(*(path_words(text) for text in brief))
    directories = tuple(word for word in words if word.endswith("/"))
    return [file for file in changed if file not in words and not file.startswith(directories)]


def check_files_named(
    item: str, sha: str | None, store: Store, record: Path, open_git: OpenGit, config: Config
) -> None:
    """Raise FilesNotNamedError when the commit changed a file its Task's brief does not name.

    Nothing is read unless the development is on, a commit is given and the id is a Task's: a
    work item, a Feature and a text that is no id are not asked, nor a sha that is no commit. The
    Task must be a started Task of a work item that is not blocked, else the complete refuses it
    in its own words; a record outside a git work tree and a commit git does not know are not
    asked, a record git ignores is. The files under the directory of the record are never asked:
    fgraph commits its own writes there. The sha is reported as given.
    """
    if not config.development.enabled or sha is None:
        return
    try:
        task_id = parse_task_id(item)
        make_commit(sha)
    except TaskIdError, CommitError:
        return
    try:
        holder = load_holder(store)(task_id)
    except TaskNotFoundError:
        return
    if isinstance(holder, BlockedWorkItem):
        return
    task = next((t for t in holder.tasks if t.id == task_id and isinstance(t, StartedTask)), None)
    work_tree = open_git(record) if task is not None else None
    if task is None or work_tree is None:
        return
    changed = work_tree.changed_files(sha)
    if changed is None:
        return
    unnamed = files_not_named(
        _outside_record(changed, record, work_tree.path),
        (task.title, task.expected_output, task.description),
    )
    if unnamed:
        raise FilesNotNamedError(
            NOT_NAMED.format(id=task_id_text(task_id), sha=sha, files=", ".join(unnamed))
        )


def _outside_record(changed: list[str], record: Path, top: Path) -> list[str]:
    """The files that are not under the directory of the record, which is inside the top."""
    prefix = f"{record.resolve().relative_to(top.resolve()).as_posix()}/"
    return [file for file in changed if not file.startswith(prefix)]
