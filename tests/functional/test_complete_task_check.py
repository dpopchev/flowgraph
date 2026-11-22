"""The criterion of the check at the complete: a Task whose check fails is not completed.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read. The
Task is started and completed in the worktree of its Story, where its work is.
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
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
ON = "[development]\nenabled = true\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


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
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def started_task(tmp_path: Path, check: str) -> Path:
    """The worktree of a started Story that holds T-0001, started, whose check is the command."""
    checkout = tmp_path / "project"
    record = checkout / ".fgraph"
    record.mkdir(parents=True)
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    (record / "config.toml").write_text(ON, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    add_task = ["add", "task", "a title", "--parent", "S-0001", "--output", "an output"]
    for argv in (ADD_STORY, [*add_task, "--check", check], ["start", "S-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    return worktree


def complete(worktree: Path) -> Outcome:
    """Complete T-0001 in the worktree, at the commit its branch is on."""
    return fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.mark.xfail(strict=True, reason="S-0089: fgraph complete runs no check of a Task yet")
class TestACompleteOfATaskWhoseCheckFails:
    @pytest.fixture
    def worktree(self, tmp_path: Path) -> Path:
        return started_task(tmp_path, "exit 2")

    def test_complete_exits_with_two_and_names_the_task_the_command_and_the_status(
        self, worktree: Path
    ) -> None:
        refused = complete(worktree)
        said = 'fgraph: error: T-0001 cannot complete: its check "exit 2" exited with status 2'
        assert (refused.status, refused.err.splitlines()[-1:]) == (2, [said])

    def test_the_task_stays_started(self, worktree: Path) -> None:
        complete(worktree)
        assert f"  S-0001  0/1 T  {TITLE}\n" in fgraph(["status"], worktree).out

    def test_nothing_is_written(self, worktree: Path) -> None:
        before = git(worktree, "rev-parse", "HEAD")
        complete(worktree)
        assert git(worktree, "rev-parse", "HEAD") == before


def test_a_complete_of_a_task_whose_check_passes_completes_it(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "true")
    assert complete(worktree).status == 0
