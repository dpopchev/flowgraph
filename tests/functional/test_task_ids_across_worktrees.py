"""The criterion of Task ids across worktrees: main and a worktree hand out no id twice.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="ST-0019: each worktree counts its own Task ids"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "ST-0002", "--output", "an output"]
WORKTREE = Path("project.worktrees") / "ST-0001-raise-the-stories-fgraph"
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
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


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
    """The checkout of main and the worktree of started ST-0001, T-0002 the highest in both."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    for argv in (ADD_STORY, ADD_OTHER, ADD_TASK, TASK_FOR_OTHER, ["start", "ST-0001"]):
        fgraph(argv, path)
    return path


def test_a_task_added_in_the_worktree_after_one_on_main_takes_the_id_after_it(
    checkout: Path, tmp_path: Path
) -> None:
    fgraph(TASK_FOR_OTHER, checkout)
    assert fgraph(ADD_TASK, tmp_path / WORKTREE).out == "added T-0004 to ST-0001\n"


def test_a_task_added_on_main_after_one_in_the_worktree_takes_the_id_after_it(
    checkout: Path, tmp_path: Path
) -> None:
    fgraph(ADD_TASK, tmp_path / WORKTREE)
    assert fgraph(TASK_FOR_OTHER, checkout).out == "added T-0004 to ST-0002\n"
