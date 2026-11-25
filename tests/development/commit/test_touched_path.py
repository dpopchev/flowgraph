"""Whether a commit of the history of HEAD changed a path, asked of the work tree (S-0080).

Run against the real git in tmp_path. The identity of every commit comes from the environment
and no git config is read.
"""

import subprocess
from pathlib import Path

import pytest

from flowgraph.development.commit import WorkTree, open_git

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


def commit(cwd: Path, name: str, message: str, *more: str) -> str:
    """Write the file of that name, commit it under the message; the sha of the commit."""
    (cwd / name).parent.mkdir(parents=True, exist_ok=True)
    (cwd / name).write_text(f"{message}\n", encoding="utf-8")
    git(cwd, "add", name, *more)
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


def test_a_file_a_commit_added_is_touched(checkout: Path) -> None:
    commit(checkout, "a.txt", "add a")
    assert work_tree(checkout).touched_path("a.txt") is True


def test_a_file_a_later_commit_deleted_is_touched(checkout: Path) -> None:
    commit(checkout, "a.txt", "add a")
    git(checkout, "rm", "--quiet", "a.txt")
    git(checkout, "commit", "--quiet", "--message", "delete a")
    assert work_tree(checkout).touched_path("a.txt") is True


def test_a_file_a_later_commit_renamed_is_touched_under_its_old_name(checkout: Path) -> None:
    commit(checkout, "a.txt", "add a")
    git(checkout, "mv", "a.txt", "b.txt")
    git(checkout, "commit", "--quiet", "--message", "rename a")
    assert work_tree(checkout).touched_path("a.txt") is True


def test_a_file_in_a_directory_is_touched_as_a_path_from_the_top(checkout: Path) -> None:
    commit(checkout, "src/pkg/module.py", "add module")
    assert work_tree(checkout, "src").touched_path("src/pkg/module.py") is True


def test_a_directory_is_not_touched(checkout: Path) -> None:
    commit(checkout, "src/pkg/module.py", "add module")
    assert work_tree(checkout, "src").touched_path("src/pkg") is False


def test_a_pattern_is_not_touched(checkout: Path) -> None:
    commit(checkout, "a.txt", "add a")
    assert work_tree(checkout).touched_path("*.txt") is False


def test_a_file_written_and_never_added_is_not_touched(checkout: Path) -> None:
    commit(checkout, "a.txt", "add a")
    (checkout / "b.txt").write_text("b\n", encoding="utf-8")
    assert work_tree(checkout).touched_path("b.txt") is False


def test_a_file_only_an_unmerged_branch_changed_is_not_touched(checkout: Path) -> None:
    commit(checkout, "a.txt", "add a")
    git(checkout, "switch", "--quiet", "--create", "wi/side")
    commit(checkout, "side.txt", "add side")
    git(checkout, "switch", "--quiet", "main")
    assert work_tree(checkout).touched_path("side.txt") is False


def test_a_file_added_and_deleted_on_a_merged_branch_is_touched(checkout: Path) -> None:
    commit(checkout, "a.txt", "add a")
    git(checkout, "switch", "--quiet", "--create", "wi/work")
    commit(checkout, "gone.txt", "add gone")
    git(checkout, "rm", "--quiet", "gone.txt")
    git(checkout, "commit", "--quiet", "--message", "delete gone")
    git(checkout, "switch", "--quiet", "main")
    commit(checkout, "main.txt", "main moves on")
    git(checkout, "merge", "--quiet", "--no-ff", "--message", "land the work", "wi/work")
    assert work_tree(checkout).touched_path("gone.txt") is True


def test_a_file_with_a_space_in_its_name_is_touched(checkout: Path) -> None:
    commit(checkout, "a b.txt", "add a b")
    assert work_tree(checkout).touched_path("a b.txt") is True


def test_a_repository_with_no_commit_answers_false(checkout: Path) -> None:
    assert work_tree(checkout).touched_path("a.txt") is False


def test_a_work_tree_built_without_touched_path_answers_false(checkout: Path) -> None:
    never = work_tree(checkout)
    bare = WorkTree(
        path=never.path,
        commit_files=never.commit_files,
        add_worktree=never.add_worktree,
        current_branch=never.current_branch,
        find_branches=never.find_branches,
        find_worktree=never.find_worktree,
        find_worktrees=never.find_worktrees,
    )
    commit(checkout, "a.txt", "add a")
    assert bare.touched_path("a.txt") is False
