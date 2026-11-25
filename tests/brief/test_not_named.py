"""The files changed that the brief of the started Task does not name: the read and its document."""

from collections.abc import Callable
from pathlib import Path
from typing import Never

import pytest

from flowgraph.brief.model import Brief
from flowgraph.brief.not_named import NotNamedError, not_named_document, not_named_of
from flowgraph.development.commit import WorkTree
from flowgraph.task.model import TaskRow
from flowgraph.work_item.views import WorkItemDetail

pytestmark = pytest.mark.view

RECORD = Path("/src/project/.fgraph")
HOME = Path("/src/project")
WORKTREE = Path("/src/project.worktrees/S-0001-a")
STARTED = TaskRow("T-0001", "Change src/a.py", "an output", "", "started")


def never(*_: object) -> Never:
    """A step of git that the read never asks for."""
    raise AssertionError("the read asks for the files uncommitted alone")


def listing(path: Path, files: list[str]) -> WorkTree:
    """A work tree at the path whose uncommitted files are those."""
    return WorkTree(
        path=path,
        commit_files=never,
        add_worktree=never,
        current_branch=never,
        find_branches=never,
        find_worktree=never,
        find_worktrees=never,
        uncommitted_files=lambda: files,
    )


def brief_of(*tasks: TaskRow, worktree: Path | None = None) -> Brief:
    """The brief of S-0001 with the Tasks, in the worktree when given."""
    detail = WorkItemDetail("S-0001", "a title", "started", "", list(tasks))
    return Brief(detail, None, worktree, None, (), ())


def not_named(files: list[str], task: TaskRow = STARTED, record: Path = RECORD) -> list[str]:
    """What not_named_of answers for a brief of the Task over a work tree that lists the files."""
    places = {record: listing(HOME, files)}
    return not_named_of(brief_of(task), record, places.__getitem__)


def test_a_file_the_brief_does_not_name_is_listed_and_one_it_names_is_not() -> None:
    assert not_named(["src/a.py", "other.txt"]) == ["other.txt"]


def test_the_files_are_listed_in_the_order_the_work_tree_gives() -> None:
    assert not_named(["docs/m.md", "src/a.py", "other.txt"]) == ["docs/m.md", "other.txt"]


@pytest.mark.parametrize(
    "task",
    [
        pytest.param(TaskRow("T-0001", "a title", "created: src/a.py", "", "started"), id="output"),
        pytest.param(
            TaskRow("T-0001", "a title", "an output", "see src/a.py", "started"), id="text"
        ),
    ],
)
def test_a_file_named_by_the_output_alone_or_the_description_alone_is_not_listed(
    task: TaskRow,
) -> None:
    assert not_named(["src/a.py"], task) == []


def test_a_file_of_the_record_is_not_listed() -> None:
    assert not_named([".fgraph/config.toml", "other.txt"]) == ["other.txt"]


def test_the_directory_of_a_record_below_the_top_is_dropped_at_its_place_alone() -> None:
    record = Path("/src/project/sub/.fgraph")
    assert not_named(["sub/.fgraph/x.toml", ".fgraph/x.toml"], record=record) == [".fgraph/x.toml"]


def test_no_file_changed_lists_nothing() -> None:
    assert not_named([]) == []


def test_the_worktree_of_the_brief_is_read_when_it_has_one() -> None:
    places = {RECORD: listing(HOME, ["h.txt"]), WORKTREE: listing(WORKTREE, ["w.txt"])}
    brief = brief_of(STARTED, worktree=WORKTREE)
    assert not_named_of(brief, RECORD, places.__getitem__) == ["w.txt"]


def test_the_work_tree_of_the_record_is_read_when_the_brief_has_no_worktree() -> None:
    places = {RECORD: listing(HOME, ["h.txt"]), WORKTREE: listing(WORKTREE, ["w.txt"])}
    assert not_named_of(brief_of(STARTED), RECORD, places.__getitem__) == ["h.txt"]


def test_the_work_tree_of_the_record_is_read_when_git_holds_none_for_the_worktree() -> None:
    places: dict[Path, WorkTree | None] = {RECORD: listing(HOME, ["h.txt"]), WORKTREE: None}
    brief = brief_of(STARTED, worktree=WORKTREE)
    assert not_named_of(brief, RECORD, places.__getitem__) == ["h.txt"]


@pytest.mark.parametrize(
    "tasks",
    [
        pytest.param([TaskRow("T-0001", "a", "b", "", "backlog")], id="backlog"),
        pytest.param([TaskRow("T-0001", "a", "b", "", "completed")], id="completed"),
        pytest.param([], id="none"),
    ],
)
def test_a_work_item_with_no_started_task_is_refused_before_git_is_asked(
    tasks: list[TaskRow],
) -> None:
    refused: Callable[[Path], Never] = never
    with pytest.raises(
        NotNamedError,
        match=r"^S-0001 has no started Task: --not-named reads the brief of the Task started$",
    ):
        not_named_of(brief_of(*tasks), RECORD, refused)


def test_a_record_outside_a_git_work_tree_is_refused() -> None:
    with pytest.raises(
        NotNamedError,
        match=r"^S-0001 has no files changed to read: the record is not inside a git work tree$",
    ):
        not_named_of(brief_of(STARTED), RECORD, lambda _: None)


def test_the_text_document_is_each_file_on_its_line() -> None:
    assert not_named_document(["a.txt", "b.txt"], "text") == "a.txt\nb.txt\n"


def test_the_text_document_of_no_file_is_empty() -> None:
    assert not_named_document([], "text") == ""


def test_the_json_document_is_a_list_and_a_newline() -> None:
    assert not_named_document(["a.txt"], "json") == '["a.txt"]\n'


def test_the_json_document_of_no_file_is_an_empty_list() -> None:
    assert not_named_document([], "json") == "[]\n"
