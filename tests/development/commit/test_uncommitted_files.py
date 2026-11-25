"""The files changed in a work tree and not committed, asked of it, against the real git.

The identity of every commit comes from the environment and no git config is read.
"""

import subprocess
from pathlib import Path

import pytest

from flowgraph.development.commit import WorkTree, open_git
from flowgraph.development.git import GitError

pytestmark = pytest.mark.edge

IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def write(cwd: Path, name: str, text: str = "a change") -> None:
    """Write the file of that name with the text, its parents made."""
    (cwd / name).parent.mkdir(parents=True, exist_ok=True)
    (cwd / name).write_text(f"{text}\n", encoding="utf-8")


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
def checkout(tmp_path: Path) -> Path:
    """A git repository on main with one commit: README and a .gitignore naming ignored.txt."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    write(path, "README", "first")
    write(path, ".gitignore", "ignored.txt")
    git(path, "add", "README", ".gitignore")
    git(path, "commit", "--quiet", "--message", "first")
    return path


def work_tree(checkout: Path, below: str = ".") -> WorkTree:
    """The work tree git finds from a directory of the checkout, as the commands open it."""
    opened = open_git(checkout / below)
    assert opened is not None
    return opened


def test_a_clean_work_tree_lists_nothing(checkout: Path) -> None:
    assert work_tree(checkout).uncommitted_files() == []


def test_a_tracked_file_changed_and_not_staged_is_listed(checkout: Path) -> None:
    write(checkout, "README")
    assert work_tree(checkout).uncommitted_files() == ["README"]


def test_a_new_file_staged_is_listed(checkout: Path) -> None:
    write(checkout, "new.txt")
    git(checkout, "add", "new.txt")
    assert work_tree(checkout).uncommitted_files() == ["new.txt"]


def test_a_new_file_not_staged_is_listed(checkout: Path) -> None:
    write(checkout, "new.txt")
    assert work_tree(checkout).uncommitted_files() == ["new.txt"]


def test_a_file_git_ignores_is_not_listed(checkout: Path) -> None:
    write(checkout, "ignored.txt")
    assert work_tree(checkout).uncommitted_files() == []


def test_a_file_in_a_directory_is_listed_as_a_path_from_the_top(checkout: Path) -> None:
    write(checkout, "src/pkg/module.py")
    assert work_tree(checkout, "src").uncommitted_files() == ["src/pkg/module.py"]


def test_a_file_removed_is_listed(checkout: Path) -> None:
    (checkout / "README").unlink()
    assert work_tree(checkout).uncommitted_files() == ["README"]


def test_a_staged_rename_is_listed_by_its_new_path(checkout: Path) -> None:
    git(checkout, "mv", "README", "NOTES")
    assert work_tree(checkout).uncommitted_files() == ["NOTES"]


def test_a_file_staged_and_changed_again_is_listed_once(checkout: Path) -> None:
    write(checkout, "README", "staged")
    git(checkout, "add", "README")
    write(checkout, "README", "changed again")
    assert work_tree(checkout).uncommitted_files() == ["README"]


def test_the_files_are_listed_sorted(checkout: Path) -> None:
    write(checkout, "b.txt")
    write(checkout, "a.txt")
    assert work_tree(checkout).uncommitted_files() == ["a.txt", "b.txt"]


def test_a_file_with_a_space_and_an_accent_is_listed_as_it_is_named(checkout: Path) -> None:
    write(checkout, "a file é.txt")
    assert work_tree(checkout).uncommitted_files() == ["a file é.txt"]


def test_a_repository_with_no_commit_raises_git_error(tmp_path: Path) -> None:
    path = tmp_path / "empty"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    with pytest.raises(GitError, match="git diff"):
        work_tree(path).uncommitted_files()
