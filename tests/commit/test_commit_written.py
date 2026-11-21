"""The commit of a write: the files the write changed, committed under its message, with fakes."""

from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Never

import pytest

from flowgraph.branch import GitError, make_slug
from flowgraph.commit import Said, WorkTree, commit_written
from flowgraph.config import make_config
from flowgraph.item import Store, ToBranch, Written
from flowgraph.story import make_story_id

pytestmark = pytest.mark.command

ON = make_config("[development]\nenabled = true\n")
OFF = make_config("")
UNCOMMITTED = make_config("[git]\ncommit = false\n")
TOP = Path("/src/project")
RECORD = TOP / ".fgraph"
FILE = RECORD / "items" / "S-0001.toml"
ADDED = Written("added S-0001\n", "chore: add S-0001 in the record")
STARTED = Written(
    "started S-0001\n",
    "chore: start S-0001 in the record",
    ToBranch(make_story_id(1), make_slug("a-slug")),
)
BRANCHED = "branch wi/S-0001-a-slug in /src/project.worktrees/S-0001-a-slug\n"


def never(*_: object) -> Never:
    """A read or a write of the record that committing a write never asks for."""
    raise AssertionError("a commit names the changed files and puts them back, no more")


def refuse(*_: object) -> Never:
    """A git step that git refuses."""
    raise GitError("git commit failed: refused")


def store(files: Sequence[Path], restored: list[str] | None = None) -> Store:
    """The store of a record whose last write changed those files; it notes a restore."""
    notes = [] if restored is None else restored
    return Store(
        find_work_item_rows=never,
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=lambda: list(files),
        restore_files=lambda: notes.append("restored"),
    )


def tree(
    commit_files: Callable[[Sequence[Path], str], str],
    add_worktree: Callable[[str, Path, str], None],
) -> WorkTree:
    """A work tree at TOP with those two steps; the commit of a write asks for no other."""
    return WorkTree(
        path=TOP,
        commit_files=commit_files,
        add_worktree=add_worktree,
        current_branch=never,
        find_branches=never,
        merge=never,
        abort_merge=never,
        commit_merge=never,
        find_worktree=never,
        remove_worktree=never,
        delete_branch=never,
        find_worktrees=never,
    )


def work_tree(steps: list[object], sha: str = "3e9ae5c0000") -> WorkTree:
    """A work tree at TOP that notes each step it is asked for and commits at that sha."""

    def commit_files(files: Sequence[Path], message: str) -> str:
        steps.append((list(files), message))
        return sha

    def add_worktree(branch: str, path: Path, commit: str) -> None:
        steps.append((branch, path, commit))

    return tree(commit_files, add_worktree)


def test_a_write_outside_a_work_tree_says_its_line_without_a_warning() -> None:
    said = commit_written(ADDED, store([FILE]), RECORD, lambda _: None, ON)
    assert said == Said("added S-0001\n")


def test_a_start_of_a_work_item_outside_a_work_tree_warns_that_no_branch_was_made() -> None:
    assert commit_written(STARTED, store([FILE]), RECORD, lambda _: None, ON) == Said(
        "started S-0001\n",
        "fgraph: warning: no branch made: /src/project/.fgraph is not inside a git work tree\n",
    )


def test_a_start_with_the_development_off_outside_a_work_tree_warns_of_nothing() -> None:
    said = commit_written(STARTED, store([FILE]), RECORD, lambda _: None, OFF)
    assert said == Said("started S-0001\n")


def test_a_start_with_the_development_off_is_committed_as_any_write() -> None:
    steps: list[object] = []
    commit_written(STARTED, store([FILE]), RECORD, lambda _: work_tree(steps), OFF)
    assert steps == [([Path(".fgraph/items/S-0001.toml")], "chore: start S-0001 in the record")]


def test_a_start_with_the_development_off_names_no_branch() -> None:
    said = commit_written(STARTED, store([FILE]), RECORD, lambda _: work_tree([]), OFF)
    assert said == Said("started S-0001\n")


@pytest.mark.parametrize("written", [ADDED, STARTED], ids=["add", "start"])
def test_a_write_with_the_commits_off_takes_no_git_step_and_says_its_line_alone(
    written: Written,
) -> None:
    steps: list[object] = []
    said = commit_written(written, store([FILE]), RECORD, lambda _: work_tree(steps), UNCOMMITTED)
    assert (steps, said) == ([], Said(written.out))


def test_a_write_with_the_commits_off_leaves_its_files_as_written() -> None:
    restored: list[str] = []
    refusing = tree(refuse, never)
    commit_written(ADDED, store([FILE], restored), RECORD, lambda _: refusing, UNCOMMITTED)
    assert restored == []


def ignoring(steps: list[object]) -> WorkTree:
    """A work tree at TOP whose git ignores the record; it notes each step it is asked for."""
    return replace(work_tree(steps), ignores=lambda path: path == RECORD)


def test_a_write_on_a_record_git_ignores_makes_no_commit() -> None:
    steps: list[object] = []
    commit_written(ADDED, store([FILE]), RECORD, lambda _: ignoring(steps), ON)
    assert steps == []


def test_a_write_on_a_record_git_ignores_says_its_line_without_a_warning() -> None:
    said = commit_written(ADDED, store([FILE]), RECORD, lambda _: ignoring([]), ON)
    assert said == Said("added S-0001\n")


def test_a_start_of_a_work_item_on_a_record_git_ignores_checks_its_branch_out_at_head() -> None:
    steps: list[object] = []
    commit_written(STARTED, store([FILE]), RECORD, lambda _: ignoring(steps), ON)
    assert steps == [("wi/S-0001-a-slug", Path("/src/project.worktrees/S-0001-a-slug"), "HEAD")]


def test_a_start_of_a_work_item_on_a_record_git_ignores_names_its_branch_without_a_warning() -> (
    None
):
    said = commit_written(STARTED, store([FILE]), RECORD, lambda _: ignoring([]), ON)
    assert said == Said(f"started S-0001\n{BRANCHED}")


def test_a_start_with_the_development_off_on_a_record_git_ignores_takes_no_git_step() -> None:
    steps: list[object] = []
    commit_written(STARTED, store([FILE]), RECORD, lambda _: ignoring(steps), OFF)
    assert steps == []


def test_a_worktree_refused_on_a_record_git_ignores_says_the_start_stays_written() -> None:
    refusing = replace(tree(never, refuse), ignores=lambda _: True)
    with pytest.raises(
        GitError,
        match=r"^git commit failed: refused -- S-0001 is started, its branch is not$",
    ):
        commit_written(STARTED, store([FILE]), RECORD, lambda _: refusing, ON)


def test_the_changed_files_are_committed_relative_to_the_top_under_the_message() -> None:
    steps: list[object] = []
    commit_written(ADDED, store([FILE]), RECORD, lambda _: work_tree(steps), ON)
    assert steps == [([Path(".fgraph/items/S-0001.toml")], "chore: add S-0001 in the record")]


def test_a_committed_write_says_its_line() -> None:
    said = commit_written(ADDED, store([FILE]), RECORD, lambda _: work_tree([]), ON)
    assert said == Said("added S-0001\n")


def test_a_write_that_changed_no_file_makes_no_commit() -> None:
    steps: list[object] = []
    commit_written(ADDED, store([]), RECORD, lambda _: work_tree(steps), ON)
    assert steps == []


def test_a_commit_refused_puts_the_files_back() -> None:
    restored: list[str] = []
    refusing = tree(refuse, never)
    with pytest.raises(GitError):
        commit_written(ADDED, store([FILE], restored), RECORD, lambda _: refusing, ON)
    assert restored == ["restored"]


def test_a_start_of_a_work_item_checks_its_branch_out_at_the_commit() -> None:
    steps: list[object] = []
    commit_written(STARTED, store([FILE]), RECORD, lambda _: work_tree(steps), ON)
    assert steps[1:] == [
        ("wi/S-0001-a-slug", Path("/src/project.worktrees/S-0001-a-slug"), "3e9ae5c0000")
    ]


def test_a_start_of_a_work_item_names_its_branch_and_its_worktree() -> None:
    said = commit_written(STARTED, store([FILE]), RECORD, lambda _: work_tree([]), ON)
    assert said == Said(f"started S-0001\n{BRANCHED}")


def test_a_worktree_refused_says_the_start_stays_committed() -> None:
    committing = tree(lambda *_: "3e9ae5c0000", refuse)
    with pytest.raises(
        GitError,
        match=r"^git commit failed: refused -- S-0001 is started at 3e9ae5c, its branch is not$",
    ):
        commit_written(STARTED, store([FILE]), RECORD, lambda _: committing, ON)


def test_a_worktree_refused_leaves_the_files_as_committed() -> None:
    restored: list[str] = []
    committing = tree(lambda *_: "3e9ae5c0000", refuse)
    with pytest.raises(GitError):
        commit_written(STARTED, store([FILE], restored), RECORD, lambda _: committing, ON)
    assert restored == []
