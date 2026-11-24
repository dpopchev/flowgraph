"""The git adapters of fgraph sync, against the real git in a temporary directory.

The identity of every commit comes from the environment and no git config is read.
"""

import subprocess
from pathlib import Path

import pytest

from flowgraph.development.sync_git import GitError, head_of, holds, merge_branch, uncommitted

pytestmark = pytest.mark.edge

BRANCH = "wi/CH-0001-a-slug"
MESSAGE = "chore: merge main into wi/CH-0001-a-slug"
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
def checkout(tmp_path: Path) -> Path:
    """A git repository on main with one commit, and BRANCH in its worktree one commit ahead."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    commit(path, "README", "a project\n")
    git(path, "worktree", "add", "--quiet", "-b", BRANCH, str(tmp_path / "branch"))
    commit(tmp_path / "branch", "work.txt", "the work\n")
    return path


@pytest.fixture
def worktree(checkout: Path, tmp_path: Path) -> Path:
    """The worktree of BRANCH, one commit ahead of main with `work.txt`."""
    return tmp_path / "branch"


def test_a_clean_worktree_lists_nothing_uncommitted(worktree: Path) -> None:
    assert uncommitted(worktree) == []


def test_a_tracked_file_changed_is_listed(worktree: Path) -> None:
    (worktree / "work.txt").write_text("changed\n", encoding="utf-8")
    assert uncommitted(worktree) == ["work.txt"]


def test_a_tracked_file_staged_is_listed(worktree: Path) -> None:
    (worktree / "work.txt").write_text("changed\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    assert uncommitted(worktree) == ["work.txt"]


def test_an_untracked_file_is_not_listed(worktree: Path) -> None:
    (worktree / "notes.txt").write_text("notes\n", encoding="utf-8")
    assert uncommitted(worktree) == []


def test_a_branch_made_at_main_holds_it(worktree: Path) -> None:
    assert holds(worktree, "main") is True


def test_a_branch_behind_a_new_commit_of_main_does_not_hold_it(
    checkout: Path, worktree: Path
) -> None:
    commit(checkout, "main.txt", "main\n")
    assert holds(worktree, "main") is False


def test_a_branch_that_is_none_raises_naming_the_command(worktree: Path) -> None:
    with pytest.raises(GitError, match=r"^git rev-list --count HEAD..refs/heads/none failed"):
        holds(worktree, "none")


@pytest.fixture
def moved(checkout: Path) -> Path:
    """The checkout after main moved on, with `main.txt` that BRANCH does not hold."""
    commit(checkout, "main.txt", "main\n")
    return checkout


def test_a_merge_answers_no_file_in_conflict(moved: Path, worktree: Path) -> None:
    assert merge_branch(worktree, "main", MESSAGE) == []


def test_a_merge_makes_a_commit_of_two_parents_under_the_message(
    moved: Path, worktree: Path
) -> None:
    before = git(worktree, "rev-parse", "HEAD")
    merge_branch(worktree, "main", MESSAGE)
    assert (
        git(worktree, "log", "-1", "--format=%s"),
        git(worktree, "log", "-1", "--format=%P"),
    ) == (
        MESSAGE,
        f"{before} {git(moved, 'rev-parse', 'main')}",
    )


def test_a_branch_with_no_commit_of_its_own_is_merged_by_a_merge_commit(
    moved: Path, tmp_path: Path
) -> None:
    behind = tmp_path / "behind"
    git(moved, "worktree", "add", "--quiet", "-b", "wi/CH-0002-none", str(behind), "main~1")
    merge_branch(behind, "main", MESSAGE)
    assert len(git(behind, "log", "-1", "--format=%P").split()) == 2


def test_the_files_main_brought_are_in_the_worktree(moved: Path, worktree: Path) -> None:
    merge_branch(worktree, "main", MESSAGE)
    assert (worktree / "main.txt").read_text(encoding="utf-8") == "main\n"


@pytest.fixture
def conflicting(checkout: Path, worktree: Path) -> Path:
    """The worktree whose BRANCH and main each wrote `shared.txt`, and `a.txt`, differently."""
    for name in ("shared.txt", "a.txt"):
        commit(checkout, name, "main\n")
        commit(worktree, name, "branch\n")
    return worktree


def test_files_both_sides_changed_are_answered_in_the_order_git_lists_them(
    conflicting: Path,
) -> None:
    assert merge_branch(conflicting, "main", MESSAGE) == ["a.txt", "shared.txt"]


def test_a_file_both_sides_changed_is_answered_as_the_conflict(
    checkout: Path, worktree: Path
) -> None:
    commit(checkout, "work.txt", "main\n")
    assert merge_branch(worktree, "main", MESSAGE) == ["work.txt"]


def test_after_a_conflict_the_head_and_the_status_are_as_they_were(conflicting: Path) -> None:
    before = git(conflicting, "rev-parse", "HEAD")
    merge_branch(conflicting, "main", MESSAGE)
    assert (git(conflicting, "rev-parse", "HEAD"), git(conflicting, "status", "--porcelain")) == (
        before,
        "",
    )


def test_after_a_conflict_no_merge_is_held(conflicting: Path) -> None:
    merge_branch(conflicting, "main", MESSAGE)
    held = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "MERGE_HEAD"],
        cwd=conflicting,
        check=False,
        capture_output=True,
    )
    assert held.returncode != 0


@pytest.fixture
def overwritten(checkout: Path, worktree: Path) -> Path:
    """The worktree holding an untracked `main.txt` that the merge of main would overwrite."""
    commit(checkout, "main.txt", "main\n")
    (worktree / "main.txt").write_text("mine\n", encoding="utf-8")
    return worktree


def test_an_untracked_file_the_merge_would_overwrite_raises_naming_the_command(
    overwritten: Path,
) -> None:
    with pytest.raises(GitError, match=r"^git merge --no-ff --no-edit --quiet --message .+ failed"):
        merge_branch(overwritten, "main", MESSAGE)


def test_an_untracked_file_the_merge_would_overwrite_stays_as_written(overwritten: Path) -> None:
    with pytest.raises(GitError):
        merge_branch(overwritten, "main", MESSAGE)
    assert (overwritten / "main.txt").read_text(encoding="utf-8") == "mine\n"


def test_the_head_is_named_by_its_short_sha(worktree: Path) -> None:
    assert head_of(worktree) == git(worktree, "rev-parse", "--short", "HEAD")
