"""The check of a completion's commit: with the development on, the repository must hold it.

The fake work tree answers what git answers for a sha: the files it changed, or None for a sha
git does not know. The check asks git for the sha it is given, and for nothing else.
"""

from pathlib import Path
from typing import Never

import pytest

from flowgraph.development.commit import WorkTree
from flowgraph.development.commit_held import CommitNotHeldError, check_commit_held
from flowgraph.record import make_config

pytestmark = pytest.mark.command

RECORD = Path("/src/project/.fgraph")
HERE = Path("/src/project")
UNKNOWN = "c6e0f15"
ON = make_config("[development]\nenabled = true\n")
OFF = make_config("")


def never(*_: object) -> Never:
    """A step of git that the check asks for in no case in which the test uses it."""
    raise AssertionError("the check asks git nothing here")


def work_tree(answer: list[str] | None, asked: list[str]) -> WorkTree:
    """A work tree whose changed_files answers that, recording each sha it is asked about."""

    def changed_files(sha: str) -> list[str] | None:
        asked.append(sha)
        return answer

    return WorkTree(
        path=HERE,
        commit_files=never,
        add_worktree=never,
        current_branch=never,
        find_branches=never,
        find_worktree=never,
        find_worktrees=never,
        changed_files=changed_files,
    )


def test_a_task_at_a_commit_that_changed_a_file_passes() -> None:
    changed = work_tree(["a.txt"], [])
    assert check_commit_held("T-0001", UNKNOWN, RECORD, lambda _: changed, ON) is None


def test_a_task_at_a_commit_that_changed_no_file_passes() -> None:
    assert check_commit_held("T-0001", UNKNOWN, RECORD, lambda _: work_tree([], []), ON) is None


def test_a_task_at_a_commit_git_does_not_know_is_refused() -> None:
    with pytest.raises(
        CommitNotHeldError,
        match=r"^T-0001 cannot complete: the repository holds no commit c6e0f15$",
    ):
        check_commit_held("T-0001", UNKNOWN, RECORD, lambda _: work_tree(None, []), ON)


@pytest.mark.parametrize("item", ["S-0001", "B-0001", "U-0001", "Q-0001"])
def test_a_work_item_at_a_commit_git_does_not_know_is_refused_naming_it(item: str) -> None:
    with pytest.raises(
        CommitNotHeldError,
        match=rf"^{item} cannot complete: the repository holds no commit c6e0f15$",
    ):
        check_commit_held(item, UNKNOWN, RECORD, lambda _: work_tree(None, []), ON)


def test_the_sha_git_is_asked_is_the_one_given() -> None:
    asked: list[str] = []
    check_commit_held("T-0001", UNKNOWN, RECORD, lambda _: work_tree([], asked), ON)
    assert asked == [UNKNOWN]


def test_with_the_development_off_a_commit_is_not_asked_of_git() -> None:
    assert check_commit_held("T-0001", UNKNOWN, RECORD, never, OFF) is None


def test_with_no_commit_given_nothing_is_asked_of_git() -> None:
    assert check_commit_held("T-0001", None, RECORD, never, ON) is None


def test_a_feature_is_left_to_the_complete() -> None:
    assert check_commit_held("F-0001", UNKNOWN, RECORD, never, ON) is None


def test_a_text_that_is_no_id_is_left_to_the_complete() -> None:
    assert check_commit_held("xyz", UNKNOWN, RECORD, never, ON) is None


def test_a_text_that_is_no_sha_is_left_to_the_complete() -> None:
    assert check_commit_held("T-0001", "xyz", RECORD, never, ON) is None


def test_outside_a_git_work_tree_nothing_is_refused() -> None:
    assert check_commit_held("T-0001", UNKNOWN, RECORD, lambda _: None, ON) is None
