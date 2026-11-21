"""The git adapters of a landing, against the real git in a temporary directory.

The identity of every commit comes from the environment and no git config is read.
"""

import subprocess
from pathlib import Path

import pytest

from flowgraph.branch import (
    GitError,
    abort_merge,
    branches_like,
    commit_merge,
    current_branch,
    delete_branch,
    merge_uncommitted,
    remove_worktree,
    worktree_of_branch,
    worktrees,
)

pytestmark = pytest.mark.edge

BRANCH = "wi/CH-0001-a-slug"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, less its last newline; fails on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.removesuffix("\n")


def commit(cwd: Path, name: str, content: str) -> None:
    """Commit the file of that name holding the content in cwd."""
    (cwd / name).write_text(content, encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "--quiet", "--message", f"write {name}")


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """The worktree of BRANCH, one commit ahead of main with `work.txt`."""
    return tmp_path / "project.worktrees" / "CH-0001-a-slug"


@pytest.fixture
def checkout(tmp_path: Path, worktree: Path) -> Path:
    """A git repository on main with one commit, and BRANCH in its worktree one commit ahead."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    commit(path, "README", "a project\n")
    git(path, "worktree", "add", "--quiet", "-b", BRANCH, str(worktree))
    commit(worktree, "work.txt", "the work\n")
    return path


def test_a_work_tree_names_the_branch_it_is_on(checkout: Path, worktree: Path) -> None:
    assert (current_branch(checkout), current_branch(worktree)) == ("main", BRANCH)


def test_the_branches_matching_a_pattern_are_listed(checkout: Path) -> None:
    git(checkout, "branch", "wi/CH-0002-other")
    assert branches_like(checkout, "wi/CH-0001-*") == [BRANCH]


def test_no_branch_matching_a_pattern_lists_none(checkout: Path) -> None:
    assert branches_like(checkout, "wi/CH-0009-*") == []


def test_a_merge_held_brings_the_work_and_makes_no_commit(checkout: Path) -> None:
    head = git(checkout, "rev-parse", "HEAD")
    merge_uncommitted(checkout, BRANCH)
    assert (git(checkout, "rev-parse", "HEAD"), git(checkout, "status", "--porcelain")) == (
        head,
        "A  work.txt",
    )


def test_a_merge_committed_joins_both_branches_under_the_message(checkout: Path) -> None:
    merge_uncommitted(checkout, BRANCH)
    commit_merge(checkout, "feat: land the work")
    parents = git(checkout, "log", "-1", "--format=%p").split()
    assert (git(checkout, "log", "-1", "--format=%s"), len(parents)) == ("feat: land the work", 2)


def test_a_merge_committed_is_named_by_its_short_sha(checkout: Path) -> None:
    merge_uncommitted(checkout, BRANCH)
    assert commit_merge(checkout, "a message") == git(checkout, "rev-parse", "--short", "HEAD")


def test_a_merge_aborted_leaves_nothing_merged(checkout: Path) -> None:
    merge_uncommitted(checkout, BRANCH)
    abort_merge(checkout)
    assert git(checkout, "status", "--porcelain") == ""


def test_an_abort_without_a_merge_changes_nothing(checkout: Path) -> None:
    abort_merge(checkout)
    assert git(checkout, "status", "--porcelain") == ""


def test_a_merge_git_refuses_raises_naming_the_command(checkout: Path) -> None:
    commit(checkout, "work.txt", "other work\n")
    with pytest.raises(GitError, match=rf"^git merge --no-ff --no-commit --quiet {BRANCH} failed"):
        merge_uncommitted(checkout, BRANCH)


def test_a_merge_git_refuses_leaves_nothing_merged(checkout: Path) -> None:
    commit(checkout, "work.txt", "other work\n")
    with pytest.raises(GitError):
        merge_uncommitted(checkout, BRANCH)
    assert git(checkout, "status", "--porcelain") == ""


def test_the_worktree_of_a_branch_is_found(checkout: Path, worktree: Path) -> None:
    assert worktree_of_branch(checkout, BRANCH) == worktree


def test_a_branch_without_a_worktree_has_none(checkout: Path) -> None:
    git(checkout, "branch", "wi/CH-0002-other")
    assert worktree_of_branch(checkout, "wi/CH-0002-other") is None


def test_the_worktrees_of_a_repository_are_listed_from_any_of_them(
    checkout: Path, worktree: Path
) -> None:
    assert worktrees(worktree) == [checkout, worktree]


def test_a_worktree_is_removed(checkout: Path, worktree: Path) -> None:
    remove_worktree(checkout, worktree)
    assert not worktree.exists()


def test_a_worktree_holding_an_untracked_file_is_not_removed(
    checkout: Path, worktree: Path
) -> None:
    (worktree / "notes.txt").write_text("not committed\n", encoding="utf-8")
    with pytest.raises(GitError, match=r"^git worktree remove .* failed"):
        remove_worktree(checkout, worktree)


def test_a_merged_branch_is_deleted(checkout: Path, worktree: Path) -> None:
    merge_uncommitted(checkout, BRANCH)
    commit_merge(checkout, "a message")
    remove_worktree(checkout, worktree)
    delete_branch(checkout, BRANCH)
    assert git(checkout, "branch", "--list", BRANCH) == ""


def test_a_branch_not_merged_is_not_deleted(checkout: Path, worktree: Path) -> None:
    remove_worktree(checkout, worktree)
    with pytest.raises(GitError, match=rf"^git branch --quiet -d {BRANCH} failed"):
        delete_branch(checkout, BRANCH)
