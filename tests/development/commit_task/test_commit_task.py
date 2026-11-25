"""The commit of the work of a started Task: the files changed that its brief names, with fakes.

The fake work tree answers uncommitted_files with a list and keeps what commit_files is given.
"""

import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.criterion import EmptyPartError, make_scenario
from flowgraph.development.commit import Said, WorkTree
from flowgraph.development.commit_task import CommitTaskError, commit_task
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
from flowgraph.story import STORY, make_story_id
from flowgraph.task import make_task, make_task_id
from flowgraph.work_item import (
    WorkItemState,
    append_task,
    blocked_work_item,
    make_work_item,
    started_task,
    started_work_item,
    work_item_row,
)

pytestmark = pytest.mark.command

HERE = Path("/src/project")
RECORD = HERE / ".fgraph"
SHA = "3e9ae5c"
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
MESSAGE = "fix: a change"


def task_texts(title: str, output: str, description: str) -> WorkItemState:
    """A started Story whose one Task, T-0001, is started and holds those three texts."""
    task = make_task(make_task_id(1), title, output, description, CREATED, "make test")
    story = make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED)
    started = started_work_item(append_task(story, task), CREATED)
    return started_task(started, make_task_id(1), CREATED)


STARTED = task_texts("a title", "changed: src/a.py", "")
BACKLOG = started_work_item(
    append_task(
        make_work_item(make_story_id(1), "a title", make_scenario("a", "b", "c"), "", CREATED),
        make_task(make_task_id(1), "a title", "changed: src/a.py", "", CREATED, "true"),
    ),
    CREATED,
)


def never(*_: object) -> Never:
    """A read or a step that the test never reaches."""
    raise AssertionError("the commit asks nothing here")


def holding(item: WorkItemState) -> Store:
    """The store of a record holding that Story alone."""
    return Store(
        find_work_item_rows=lambda kind: [work_item_row(item)] if kind == STORY else [],
        load_work_item=lambda _: item,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
    )


def work_tree(changed: list[str], commit_files: Callable[[Sequence[Path], str], str]) -> WorkTree:
    """A work tree at HERE with those files changed and that commit_files."""
    return WorkTree(
        path=HERE,
        commit_files=commit_files,
        add_worktree=never,
        current_branch=never,
        find_branches=never,
        find_worktree=never,
        find_worktrees=never,
        uncommitted_files=lambda: changed,
    )


def committed(changed: list[str]) -> tuple[Said, Sequence[Path], str]:
    """Commit T-0001, the work tree having those files changed: what it said, was given."""
    given: list[tuple[Sequence[Path], str]] = []

    def commit_files(files: Sequence[Path], message: str) -> str:
        given.append((files, message))
        return SHA

    tree = work_tree(changed, commit_files)
    said = commit_task("T-0001", MESSAGE, holding(STARTED), RECORD, lambda _: tree)
    return said, given[0][0], given[0][1]


def refused(changed: list[str], item: WorkItemState, said: str) -> None:
    """Assert that the commit raises CommitTaskError saying exactly that; nothing committed."""
    tree = work_tree(changed, never)
    with pytest.raises(CommitTaskError, match=f"^{re.escape(said)}$"):
        commit_task("T-0001", MESSAGE, holding(item), RECORD, lambda _: tree)


def test_it_says_the_commit_of_the_task_at_the_sha() -> None:
    assert committed(["src/a.py"])[0].out == "committed T-0001 of S-0001 at 3e9ae5c\n"


def test_it_commits_the_file_the_brief_names() -> None:
    assert committed(["src/a.py"])[1] == [Path("src/a.py")]


def test_its_message_ends_with_the_ids_of_the_work_item_and_the_task() -> None:
    assert committed(["src/a.py"])[2] == "fix: a change (S-0001, T-0001)"


def test_a_file_of_the_record_is_not_committed() -> None:
    assert committed([".fgraph/stories/S-0001.toml", "src/a.py"])[1] == [Path("src/a.py")]


def test_a_task_in_the_backlog_is_refused() -> None:
    said = "T-0001 is not started: fgraph commit commits the work of the Task started"
    refused(["src/a.py"], BACKLOG, said)


def test_a_task_of_a_blocked_work_item_is_refused() -> None:
    said = "T-0001 is not started: fgraph commit commits the work of the Task started"
    refused(["src/a.py"], blocked_work_item(STARTED, "no key", "developer", CREATED), said)


def test_a_record_outside_a_git_work_tree_is_refused() -> None:
    said = "T-0001 has no files to commit: the record is not inside a git work tree"
    with pytest.raises(CommitTaskError, match=f"^{re.escape(said)}$"):
        commit_task("T-0001", MESSAGE, holding(STARTED), RECORD, lambda _: None)


def test_no_file_changed_is_refused() -> None:
    said = "T-0001 has nothing to commit: no file is changed in /src/project"
    refused([], STARTED, said)


def test_a_file_the_brief_does_not_name_is_refused_naming_it() -> None:
    said = (
        "T-0001 cannot commit: its brief does not name other.txt -- nothing is committed; "
        "take each back or have the brief name it"
    )
    refused(["src/a.py", "other.txt"], STARTED, said)


def test_a_blank_message_is_refused() -> None:
    with pytest.raises(EmptyPartError):
        commit_task("T-0001", "  ", holding(STARTED), RECORD, never)
