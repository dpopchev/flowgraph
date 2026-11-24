"""The criterion of B-0029: with the development on, a commit the repository lacks is refused.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read. The
red tests are marked xfail (strict) until the check of the commit is wired into the complete.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run, run_gate

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
ADD_TASK = ["add", "task", "a title", "--parent", "S-0001", "--output", "an output"]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
ON = "[development]\nenabled = true\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
UNKNOWN = "c6e0f15"
NOT_HELD = "fgraph: error: {id} cannot complete: the repository holds no commit {sha}"
XFAIL = pytest.mark.xfail(
    strict=True, reason="B-0029: a commit the repository does not hold is taken"
)


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on its files and the real git."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        now=lambda: NOW,
        open_git=open_git,
        load_config=read_config,
        run_gate=run_gate,
        run_check=run_gate,
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def not_held(item: str, sha: str) -> str:
    """The last line of a refusal of a commit the repository does not hold."""
    return NOT_HELD.format(id=item, sha=sha)


def started_task(tmp_path: Path, check: str) -> Path:
    """The worktree of a started Story that holds T-0001, started, whose check is the command."""
    checkout = tmp_path / "project"
    record = checkout / ".fgraph"
    record.mkdir(parents=True)
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    (record / "config.toml").write_text(ON, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    add_task = [*ADD_TASK, "--check", check]
    for argv in (ADD_STORY, add_task, ["start", "S-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    return worktree


def commit_file(cwd: Path, name: str) -> None:
    """Write a file in cwd and commit it alone."""
    (cwd / name).write_text("text\n", encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "--quiet", "--message", f"feat: add {name}")


def complete_at(cwd: Path, sha: str, item: str = "T-0001") -> Outcome:
    """Complete the item in cwd at the commit given."""
    return fgraph(["complete", item, "--commit", sha], cwd)


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
    return started_task(tmp_path, "true")


@XFAIL
class TestATaskCompletedAtACommitTheRepositoryDoesNotHold:
    def test_complete_exits_with_two_and_names_the_task_and_the_commit(
        self, worktree: Path
    ) -> None:
        refused = complete_at(worktree, UNKNOWN)
        assert (refused.status, refused.err.splitlines()[-1:]) == (
            2,
            [not_held("T-0001", UNKNOWN)],
        )

    def test_the_branch_stays_on_the_commit_it_was_on(self, worktree: Path) -> None:
        before = git(worktree, "rev-parse", "HEAD")
        complete_at(worktree, UNKNOWN)
        assert git(worktree, "rev-parse", "HEAD") == before

    def test_the_task_stays_started(self, worktree: Path) -> None:
        complete_at(worktree, UNKNOWN)
        assert f"  S-0001  0/1 T  {TITLE}\n" in fgraph(["status"], worktree).out


@XFAIL
def test_the_sha_of_a_tree_is_refused(worktree: Path) -> None:
    tree = git(worktree, "rev-parse", "HEAD^{tree}")
    refused = complete_at(worktree, tree)
    assert (refused.status, refused.err.splitlines()[-1:]) == (2, [not_held("T-0001", tree)])


@XFAIL
def test_the_check_of_the_task_is_not_run_for_a_commit_the_repository_does_not_hold(
    tmp_path: Path,
) -> None:
    worktree = started_task(tmp_path, "exit 3")
    refused = complete_at(worktree, UNKNOWN)
    assert refused.err.splitlines()[-1:] == [not_held("T-0001", UNKNOWN)]


@XFAIL
class TestAStoryCompletedOnMainAtACommitTheRepositoryDoesNotHold:
    @pytest.fixture
    def merged(self, tmp_path: Path) -> Path:
        worktree = started_task(tmp_path, "true")
        commit_file(worktree, "work.txt")
        complete_at(worktree, git(worktree, "rev-parse", "HEAD"))
        checkout = tmp_path / "project"
        git(checkout, "merge", "--quiet", "--no-ff", "--message", "feat: land S-0001", BRANCH)
        return checkout

    def test_complete_exits_with_two_and_names_the_story_and_the_commit(
        self, merged: Path
    ) -> None:
        refused = complete_at(merged, UNKNOWN, "S-0001")
        assert (refused.status, refused.err.splitlines()[-1:]) == (
            2,
            [not_held("S-0001", UNKNOWN)],
        )

    def test_the_checkout_stays_on_the_commit_it_was_on(self, merged: Path) -> None:
        before = git(merged, "rev-parse", "HEAD")
        complete_at(merged, UNKNOWN, "S-0001")
        assert git(merged, "rev-parse", "HEAD") == before


@XFAIL
def test_a_task_of_a_record_git_ignores_is_refused_the_same(tmp_path: Path) -> None:
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    (checkout / ".gitignore").write_text(".fgraph/\n", encoding="utf-8")
    git(checkout, "add", ".gitignore")
    git(checkout, "commit", "--quiet", "--message", "first")
    (checkout / ".fgraph").mkdir()
    (checkout / ".fgraph" / "config.toml").write_text(ON, encoding="utf-8")
    add_task = [*ADD_TASK, "--check", "true"]
    for argv in (ADD_STORY, add_task, ["start", "S-0001"], ["start", "T-0001"]):
        fgraph(argv, checkout)
    refused = complete_at(checkout, UNKNOWN)
    assert (refused.status, refused.err.splitlines()[-1:]) == (2, [not_held("T-0001", UNKNOWN)])


@pytest.mark.parametrize("args", [("rev-parse", "HEAD"), ("rev-parse", "--short", "HEAD")])
def test_a_task_completed_at_the_commit_its_branch_is_on_is_completed(
    worktree: Path, args: tuple[str, ...]
) -> None:
    sha = git(worktree, *args)
    done = complete_at(worktree, sha)
    assert (done.status, done.out) == (0, f"completed T-0001 of S-0001 at {sha}\n")


def test_a_task_completed_at_a_commit_of_main_its_branch_does_not_hold_is_completed(
    worktree: Path, tmp_path: Path
) -> None:
    checkout = tmp_path / "project"
    commit_file(checkout, "main.txt")
    done = complete_at(worktree, git(checkout, "rev-parse", "HEAD"))
    assert done.status == 0


def test_any_sha_is_taken_with_the_development_off(tmp_path: Path) -> None:
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    git(checkout, "commit", "--quiet", "--allow-empty", "--message", "first")
    for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"], ["start", "T-0001"]):
        fgraph(argv, checkout)
    done = complete_at(checkout, UNKNOWN)
    assert (done.status, done.out) == (0, f"completed T-0001 of S-0001 at {UNKNOWN}\n")


def test_any_sha_is_taken_outside_a_git_work_tree(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    (plain / ".fgraph").mkdir(parents=True)
    (plain / ".fgraph" / "config.toml").write_text(ON, encoding="utf-8")
    add_task = [*ADD_TASK, "--check", "true"]
    for argv in (ADD_STORY, add_task, ["start", "S-0001"], ["start", "T-0001"]):
        fgraph(argv, plain)
    done = complete_at(plain, UNKNOWN)
    assert (done.status, done.out) == (0, f"completed T-0001 of S-0001 at {UNKNOWN}\n")


def test_a_text_that_is_no_sha_keeps_its_refusal(worktree: Path) -> None:
    refused = complete_at(worktree, "xyz")
    assert (refused.status, refused.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: 'xyz' is no commit: it is 7 to 40 hex digits"],
    )
