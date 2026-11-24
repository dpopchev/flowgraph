"""The remove of a Task with the development on: written in the worktree of its work item.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
DROP_WAITING = ["remove", "T-0002", "--reason", "not needed"]
DROP_STARTED = ["remove", "T-0001", "--reason", "folded into T-0003"]
LAND = ["land", "S-0001", "--message", "feat: land it"]
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def task(number: int) -> list[str]:
    """The command that adds the Task of that number to S-0001, with the check it takes."""
    added = ["add", "task", f"task {number}", "--parent", "S-0001", "--output", "an output"]
    return [*added, "--check", "true"]


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
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def turn_development_on(checkout: Path) -> None:
    """Commit `[development] enabled = true` as the config.toml of the record of the checkout."""
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")


def complete(task_id: str, worktree: Path) -> Outcome:
    """Complete the Task of that id in the worktree, in the commit its branch is at."""
    return fgraph(["complete", task_id, "--commit", git(worktree, "rev-parse", "HEAD")], worktree)


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
    """The checkout of main: S-0001 with three Tasks, started on its worktree branch."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    turn_development_on(path)
    for argv in (ADD_STORY, task(1), task(2), task(3), ["start", "S-0001"]):
        fgraph(argv, path)
    return path


@pytest.fixture
def worktree(checkout: Path, tmp_path: Path) -> Path:
    """The worktree of the started Story, its first Task started there."""
    path = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], path)
    return path


def test_a_task_removed_in_the_worktree_is_one_commit_of_its_branch(worktree: Path) -> None:
    outcome = fgraph(DROP_WAITING, worktree)
    assert (
        outcome.status,
        outcome.out,
        git(worktree, "log", "-1", "--format=%s"),
        git(worktree, "show", "--name-only", "--format=", "HEAD"),
    ) == (
        0,
        "removed T-0002 of S-0001\n",
        "chore: remove T-0002 of S-0001 in the record",
        ".fgraph/items/S-0001.toml",
    )


def test_a_task_removed_on_main_is_refused_naming_the_worktree_and_writes_nothing(
    checkout: Path, worktree: Path
) -> None:
    outcome = fgraph(DROP_WAITING, checkout)
    assert (
        outcome.status,
        outcome.err.splitlines()[-1:],
        git(checkout, "status", "--porcelain"),
        git(checkout, "log", "-1", "--format=%s"),
    ) == (
        2,
        [f"fgraph: error: S-0001 is started: its Tasks are written in its worktree, {worktree}"],
        "",
        "chore: start S-0001 in the record",
    )


def test_a_story_whose_tasks_are_completed_or_removed_lands(checkout: Path, worktree: Path) -> None:
    for argv in (DROP_WAITING, DROP_STARTED, ["start", "T-0003"]):
        fgraph(argv, worktree)
    complete("T-0003", worktree)
    outcome = fgraph(LAND, checkout)
    assert (outcome.status, outcome.out.startswith("landed S-0001 at")) == (0, True)


def test_a_story_with_tasks_in_backlog_is_refused_its_landing(
    checkout: Path, worktree: Path
) -> None:
    complete("T-0001", worktree)
    outcome = fgraph(LAND, checkout)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: S-0001 has Tasks to complete first: T-0002, T-0003"],
    )
