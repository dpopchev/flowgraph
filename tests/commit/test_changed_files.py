"""The files a commit changed, asked of the work tree, against the real git in tmp_path.

The identity of every commit comes from the environment and no git config is read.
"""

import subprocess
from pathlib import Path

import pytest

from flowgraph.commit import WorkTree, open_git

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


def commit(cwd: Path, name: str, message: str) -> str:
    """Write the file of that name, commit it under the message; the sha of the commit."""
    (cwd / name).parent.mkdir(parents=True, exist_ok=True)
    (cwd / name).write_text(f"{message}\n", encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "--quiet", "--message", message)
    return git(cwd, "rev-parse", "HEAD")


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
    """A git repository on main with no commit."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    return path


def work_tree(checkout: Path, below: str = ".") -> WorkTree:
    """The work tree git finds from a directory of the checkout, as the commands open it."""
    opened = open_git(checkout / below)
    assert opened is not None
    return opened


def test_the_first_commit_answers_with_the_files_it_added(checkout: Path) -> None:
    sha = commit(checkout, "README", "first")
    assert work_tree(checkout).changed_files(sha) == ["README"]


def test_a_commit_answers_with_the_files_it_changed_alone(checkout: Path) -> None:
    commit(checkout, "README", "first")
    sha = commit(checkout, "other.txt", "second")
    assert work_tree(checkout).changed_files(sha) == ["other.txt"]


def test_a_file_in_a_directory_is_answered_as_a_path_from_the_top(checkout: Path) -> None:
    commit(checkout, "README", "first")
    sha = commit(checkout, "src/pkg/module.py", "second")
    assert work_tree(checkout, "src").changed_files(sha) == ["src/pkg/module.py"]


def test_a_file_with_a_space_and_an_accent_is_answered_as_it_is_named(checkout: Path) -> None:
    sha = commit(checkout, "a file é.txt", "first")
    assert work_tree(checkout).changed_files(sha) == ["a file é.txt"]


def test_a_merge_commit_answers_with_what_it_brought_to_its_first_parent(checkout: Path) -> None:
    commit(checkout, "README", "first")
    git(checkout, "switch", "--quiet", "--create", "wi/work")
    commit(checkout, "work.txt", "the work")
    git(checkout, "switch", "--quiet", "main")
    commit(checkout, "main.txt", "main moves on")
    git(checkout, "merge", "--quiet", "--no-ff", "--message", "land the work", "wi/work")
    merge = git(checkout, "rev-parse", "HEAD")
    assert work_tree(checkout).changed_files(merge) == ["work.txt"]


def test_a_sha_git_does_not_know_answers_with_none(checkout: Path) -> None:
    commit(checkout, "README", "first")
    assert work_tree(checkout).changed_files("0" * 40) is None
