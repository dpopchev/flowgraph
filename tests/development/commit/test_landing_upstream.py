"""The upstream step of a landing: the remote main tracks, against the real git in tmp_path.

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
    """The output of the git command run in cwd, stripped; fails on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def commit(cwd: Path, name: str) -> None:
    """Commit a file of that name in cwd."""
    (cwd / name).write_text(f"{name}\n", encoding="utf-8")
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
def origin(tmp_path: Path) -> Path:
    """A bare repository on main."""
    path = tmp_path / "origin.git"
    git(tmp_path, "init", "--quiet", "--bare", "--initial-branch", "main", str(path))
    return path


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A git repository on main with one commit and no remote."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    commit(path, "README")
    return path


@pytest.fixture
def tracking(checkout: Path, origin: Path) -> Path:
    """The checkout with main pushed to the origin and tracking it."""
    git(checkout, "remote", "add", "origin", str(origin))
    git(checkout, "push", "--quiet", "--set-upstream", "origin", "main")
    return checkout


def work_tree(checkout: Path) -> WorkTree:
    """The work tree git finds from the checkout, as the commands open it."""
    opened = open_git(checkout)
    assert opened is not None
    return opened


def test_the_upstream_of_main_is_the_remote_main_tracks_and_its_ref(tracking: Path) -> None:
    assert work_tree(tracking).landing.upstream("main") == ("origin", "refs/heads/main")


def test_the_upstream_of_a_main_that_tracks_no_remote_is_refused(checkout: Path) -> None:
    with pytest.raises(GitError, match=r"^main tracks no branch of a remote to push to$"):
        work_tree(checkout).landing.upstream("main")
