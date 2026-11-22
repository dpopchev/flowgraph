"""The git adapters of a branch, against the real git in a temporary directory.

The identity of every commit comes from the environment and no git config is read.
"""

import subprocess
from pathlib import Path

import pytest

from flowgraph.development.git import GitError, add_worktree, commit_files, ignores, work_tree_of

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
    """The identity of every commit from the environment, and no git config of the machine."""
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


def test_a_directory_inside_a_work_tree_names_its_top(checkout: Path) -> None:
    inside = checkout / ".fgraph"
    inside.mkdir()
    assert work_tree_of(inside) == checkout


def test_a_directory_outside_any_work_tree_names_none(tmp_path: Path) -> None:
    assert work_tree_of(tmp_path) is None


def test_a_directory_a_rule_names_is_ignored(checkout: Path) -> None:
    (checkout / ".gitignore").write_text(".fgraph/\n", encoding="utf-8")
    (checkout / ".fgraph").mkdir()
    assert ignores(checkout, checkout / ".fgraph") is True


def test_a_directory_no_rule_names_is_not_ignored(checkout: Path) -> None:
    (checkout / ".fgraph").mkdir()
    assert ignores(checkout, checkout / ".fgraph") is False


def test_a_directory_a_rule_names_is_ignored_while_a_file_of_it_is_tracked(checkout: Path) -> None:
    (checkout / ".fgraph").mkdir()
    (checkout / ".fgraph" / "item.toml").write_text("id = 1\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/item.toml")
    git(checkout, "commit", "--quiet", "--message", "track the item")
    (checkout / ".gitignore").write_text(".fgraph/\n", encoding="utf-8")
    assert ignores(checkout, checkout / ".fgraph") is True


def test_a_path_relative_to_the_working_directory_is_asked_of_from_there(
    checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (checkout / ".gitignore").write_text(".fgraph/\n", encoding="utf-8")
    (checkout / ".fgraph").mkdir()
    (checkout / "inside").mkdir()
    monkeypatch.chdir(checkout / "inside")
    assert ignores(checkout, Path("../.fgraph")) is True


def test_a_path_git_cannot_tell_of_raises_naming_the_command(
    checkout: Path, tmp_path: Path
) -> None:
    with pytest.raises(GitError, match=r"^git check-ignore .* failed: .*outside repository"):
        ignores(checkout, tmp_path / "elsewhere")


def test_a_new_file_is_committed_with_its_message(checkout: Path) -> None:
    (checkout / "item.toml").write_text("id = 1\n", encoding="utf-8")
    commit_files(checkout, [Path("item.toml")], "chore: write the item")
    assert git(checkout, "log", "-1", "--format=%B") == "chore: write the item\n"


def test_the_commit_is_named_by_its_sha(checkout: Path) -> None:
    (checkout / "item.toml").write_text("id = 1\n", encoding="utf-8")
    assert commit_files(checkout, [Path("item.toml")], "a message") == git(
        checkout, "rev-parse", "HEAD"
    )


def test_the_commit_holds_only_the_file_named(checkout: Path) -> None:
    (checkout / "item.toml").write_text("id = 1\n", encoding="utf-8")
    (checkout / "other.txt").write_text("staged\n", encoding="utf-8")
    git(checkout, "add", "other.txt")
    (checkout / "README").write_text("changed\n", encoding="utf-8")
    commit_files(checkout, [Path("item.toml")], "a message")
    assert git(checkout, "show", "--name-only", "--format=", "HEAD") == "item.toml"


def test_what_else_was_staged_or_changed_stays_so(checkout: Path) -> None:
    (checkout / "item.toml").write_text("id = 1\n", encoding="utf-8")
    (checkout / "other.txt").write_text("staged\n", encoding="utf-8")
    git(checkout, "add", "other.txt")
    (checkout / "README").write_text("changed\n", encoding="utf-8")
    commit_files(checkout, [Path("item.toml")], "a message")
    assert git(checkout, "status", "--porcelain").splitlines() == [" M README", "A  other.txt"]


def test_a_commit_git_refuses_raises_naming_the_command(checkout: Path) -> None:
    with pytest.raises(GitError, match=r"^git add -- missing.toml failed: .*missing\.toml"):
        commit_files(checkout, [Path("missing.toml")], "a message")


def test_several_files_are_held_by_one_commit(checkout: Path) -> None:
    (checkout / "item.toml").write_text("id = 1\n", encoding="utf-8")
    (checkout / "queue.toml").write_text("backlog = []\n", encoding="utf-8")
    commit_files(checkout, [Path("item.toml"), Path("queue.toml")], "a message")
    assert git(checkout, "show", "--name-only", "--format=", "HEAD").splitlines() == [
        "item.toml",
        "queue.toml",
    ]


def test_several_files_git_refuses_to_commit_are_left_unstaged(checkout: Path) -> None:
    hook = checkout / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    (checkout / "item.toml").write_text("id = 1\n", encoding="utf-8")
    (checkout / "README").write_text("changed\n", encoding="utf-8")
    with pytest.raises(GitError):
        commit_files(checkout, [Path("item.toml"), Path("README")], "a message")
    assert git(checkout, "status", "--porcelain").splitlines() == [" M README", "?? item.toml"]


def test_a_worktree_is_added_on_a_new_branch_at_the_commit(checkout: Path, tmp_path: Path) -> None:
    worktree = tmp_path / "project.worktrees" / "CH-0001-a-slug"
    head = git(checkout, "rev-parse", "HEAD")
    add_worktree(checkout, "wi/CH-0001-a-slug", worktree, head)
    assert (
        git(worktree, "branch", "--show-current"),
        git(worktree, "rev-parse", "HEAD"),
    ) == ("wi/CH-0001-a-slug", head)


def test_a_worktree_on_a_branch_that_exists_raises_naming_the_command(
    checkout: Path, tmp_path: Path
) -> None:
    git(checkout, "branch", "wi/CH-0001-a-slug")
    with pytest.raises(GitError, match=r"^git worktree add .* failed: .*already exists"):
        add_worktree(checkout, "wi/CH-0001-a-slug", tmp_path / "elsewhere", "HEAD")


def test_a_commit_git_refuses_leaves_the_file_unstaged(checkout: Path) -> None:
    hook = checkout / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    (checkout / "README").write_text("changed\n", encoding="utf-8")
    with pytest.raises(GitError):
        commit_files(checkout, [Path("README")], "a message")
    assert git(checkout, "status", "--porcelain") == " M README"
