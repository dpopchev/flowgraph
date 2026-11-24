"""The git adapter of a landing through a pull request, against the real git and a bare origin.

The identity of every commit comes from the environment and no git config is read.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from flowgraph.development.commit import open_git
from flowgraph.development.git import GitError
from flowgraph.development.pull_git import push_beside

pytestmark = pytest.mark.edge

IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
BRANCH = "wi/S-0001-a-slug"


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


def branched(checkout: Path) -> Path:
    """The checkout with the branch of a work item one commit ahead of main, back on main."""
    git(checkout, "switch", "--quiet", "--create", BRANCH)
    commit(checkout, "work.txt")
    git(checkout, "switch", "--quiet", "main")
    return checkout


@pytest.fixture
def tracking(checkout: Path, origin: Path) -> Path:
    """The checkout whose main is pushed to the origin and tracks it, the branch made after."""
    git(checkout, "remote", "add", "origin", str(origin))
    git(checkout, "push", "--quiet", "--set-upstream", "origin", "main")
    return branched(checkout)


def test_a_push_beside_main_names_the_remote_main_tracks(tracking: Path) -> None:
    assert push_beside(tracking, BRANCH, "main") == "origin"


def test_a_push_beside_main_puts_the_branch_on_the_origin_at_its_commit(
    tracking: Path, origin: Path
) -> None:
    push_beside(tracking, BRANCH, "main")
    assert git(origin, "rev-parse", BRANCH) == git(tracking, "rev-parse", BRANCH)


def test_a_push_beside_main_leaves_main_of_the_origin_where_it_was(
    tracking: Path, origin: Path
) -> None:
    before = git(origin, "rev-parse", "main")
    push_beside(tracking, BRANCH, "main")
    assert git(origin, "rev-parse", "main") == before


def test_a_second_push_after_a_new_commit_moves_the_branch_of_the_origin(
    tracking: Path, origin: Path
) -> None:
    push_beside(tracking, BRANCH, "main")
    git(tracking, "switch", "--quiet", BRANCH)
    commit(tracking, "more.txt")
    push_beside(tracking, BRANCH, "main")
    assert git(origin, "rev-parse", BRANCH) == git(tracking, "rev-parse", BRANCH)


def test_a_push_beside_a_main_that_tracks_no_branch_raises_naming_it(checkout: Path) -> None:
    with pytest.raises(GitError, match=r"^main tracks no branch of a remote to push to$"):
        push_beside(branched(checkout), BRANCH, "main")


def test_a_push_to_a_removed_origin_raises_naming_the_command(tracking: Path, origin: Path) -> None:
    shutil.rmtree(origin)
    with pytest.raises(GitError, match=r"^git push "):
        push_beside(tracking, BRANCH, "main")


def test_the_work_tree_of_open_git_publishes_through_the_push_beside(tracking: Path) -> None:
    work_tree = open_git(tracking)
    published = None if work_tree is None else work_tree.landing.publish(BRANCH, "main")
    assert published == "origin"
