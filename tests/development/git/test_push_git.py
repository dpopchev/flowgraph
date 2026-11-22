"""The git adapter of the push of a landing, against the real git and a bare origin.

The identity of every commit comes from the environment and no git config is read.
"""

import subprocess
from pathlib import Path

import pytest

from flowgraph.development.git import GitError, push

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
    """The checkout with main pushed to the origin and tracking it, then one commit ahead."""
    git(checkout, "remote", "add", "origin", str(origin))
    git(checkout, "push", "--quiet", "--set-upstream", "origin", "main")
    commit(checkout, "work.txt")
    return checkout


def test_a_push_moves_main_of_the_origin_to_main_of_the_work_tree(
    tracking: Path, origin: Path
) -> None:
    push(tracking, "main")
    assert git(origin, "rev-parse", "main") == git(tracking, "rev-parse", "main")


def test_a_push_names_the_remote_it_pushed_to(tracking: Path) -> None:
    assert push(tracking, "main") == "origin"


def test_a_push_of_a_branch_that_tracks_no_remote_raises_naming_it(checkout: Path) -> None:
    with pytest.raises(GitError, match=r"^main tracks no branch of a remote to push to$"):
        push(checkout, "main")


def test_a_push_to_a_remote_git_cannot_reach_raises_naming_the_command(
    tracking: Path, origin: Path
) -> None:
    origin.rename(origin.with_name("moved.git"))
    with pytest.raises(
        GitError, match=r"^git push --quiet origin refs/heads/main:refs/heads/main failed: "
    ):
        push(tracking, "main")
