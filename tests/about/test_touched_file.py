"""Whether a commit of the history of HEAD changed the file a text names (S-0080)."""

from collections.abc import Callable
from pathlib import Path
from typing import Never

import pytest

from flowgraph.about.file import is_touched
from flowgraph.development.commit import WorkTree

pytestmark = pytest.mark.view

TOP = Path("/src/project")


def never(*_: object) -> Never:
    """A step of git that the question never asks for."""
    raise AssertionError("is_touched asks git only whether a commit touched the path")


def tree(touched: Callable[[str], bool]) -> WorkTree:
    """The work tree at the top of the project, answering only `touched_path`."""
    return WorkTree(
        path=TOP,
        commit_files=never,
        add_worktree=never,
        current_branch=never,
        find_branches=never,
        find_worktree=never,
        find_worktrees=never,
        touched_path=touched,
    )


def test_a_file_a_commit_changed_is_touched() -> None:
    assert is_touched("work.txt", TOP, lambda _: tree(lambda _: True)) is True


def test_a_file_no_commit_changed_is_not_touched() -> None:
    assert is_touched("work.txt", TOP, lambda _: tree(lambda _: False)) is False


@pytest.mark.parametrize(
    ("directory", "text", "asked"),
    [(TOP / "sub", "a.txt", "sub/a.txt"), (TOP / "sub", "../work.txt", "work.txt")],
    ids=["below", "up"],
)
def test_git_is_asked_the_path_from_the_top(directory: Path, text: str, asked: str) -> None:
    seen: list[str] = []

    def touched(path: str) -> bool:
        seen.append(path)
        return True

    is_touched(text, directory, lambda _: tree(touched))
    assert seen == [asked]


def test_a_directory_inside_no_work_tree_is_not_touched() -> None:
    assert is_touched("work.txt", TOP, lambda _: None) is False


def test_a_path_that_leads_out_of_the_work_tree_is_not_touched() -> None:
    assert is_touched("../elsewhere.txt", TOP, lambda _: tree(never)) is False
