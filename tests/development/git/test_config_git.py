"""The adapter that reads the key fgraph.record, against the real git in a temporary directory.

The identity of every commit comes from the environment; the global configuration is a file of
the test, so the one key read is the one the test sets.
"""

import subprocess
from pathlib import Path

import pytest

from flowgraph.development.config_git import record_named

pytestmark = pytest.mark.edge

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


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and an empty global configuration."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A git repository on main with one commit, holding `README`."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / "README").write_text("a project\n", encoding="utf-8")
    git(path, "add", "README")
    git(path, "commit", "--quiet", "--message", "first")
    return path


def test_no_key_names_none(checkout: Path) -> None:
    assert record_named(checkout) is None


def test_the_key_names_the_folder_under_the_top(checkout: Path) -> None:
    git(checkout, "config", "fgraph.record", ".dpopchev")
    assert record_named(checkout) == checkout / ".dpopchev"


def test_the_folder_need_not_be_there(checkout: Path) -> None:
    git(checkout, "config", "fgraph.record", ".dpopchev")
    folder = checkout / ".dpopchev"
    assert (record_named(checkout), folder.exists()) == (folder, False)


def test_a_subdirectory_names_the_same_folder(checkout: Path) -> None:
    git(checkout, "config", "fgraph.record", ".dpopchev")
    (checkout / "src").mkdir()
    assert record_named(checkout / "src") == checkout / ".dpopchev"


def test_a_folder_of_two_parts_is_joined_to_the_top(checkout: Path) -> None:
    git(checkout, "config", "fgraph.record", "docs/record")
    assert record_named(checkout) == checkout / "docs" / "record"


def test_a_directory_outside_any_work_tree_names_none(tmp_path: Path) -> None:
    assert record_named(tmp_path) is None


def test_an_empty_value_names_none(checkout: Path) -> None:
    git(checkout, "config", "fgraph.record", "")
    assert record_named(checkout) is None


def test_a_key_of_the_global_configuration_alone_names_none(checkout: Path, tmp_path: Path) -> None:
    git(checkout, "config", "--file", str(tmp_path / "gitconfig"), "fgraph.record", ".dpopchev")
    assert record_named(checkout) is None


def test_a_second_worktree_names_the_folder_under_its_own_top(
    checkout: Path, tmp_path: Path
) -> None:
    git(checkout, "config", "fgraph.record", ".dpopchev")
    other = tmp_path / "other"
    git(checkout, "worktree", "add", "--quiet", "-b", "wi/other", str(other))
    assert record_named(other) == other / ".dpopchev"
