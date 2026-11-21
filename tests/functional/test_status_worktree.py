"""The criterion of status across worktrees: on main it reads a started work item where its
Tasks are written, in its worktree.

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

pytestmark = pytest.mark.functional

NOT_YET = pytest.mark.xfail(
    strict=True, reason="ST-0035: status on main reads the record of main alone yet"
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
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
    """The checkout of main of a repository with ST-0001 started, its two Tasks in Backlog."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    for argv in (ADD_STORY, ADD_TASK, ADD_TASK, ["start", "ST-0001"]):
        fgraph(argv, path)
    return path


class TestAStoryWithOneOfItsTwoTasksCompletedInItsWorktree:
    @pytest.fixture
    def listed(self, checkout: Path, tmp_path: Path) -> Outcome:
        for argv in (["start", "T-0001"], ["complete", "T-0001", "--commit", "abc1234"]):
            fgraph(argv, tmp_path / WORKTREE)
        return fgraph(["status"], checkout)

    def test_status_on_main_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    @NOT_YET
    def test_status_on_main_lists_the_story_with_the_tasks_its_worktree_holds(
        self, listed: Outcome
    ) -> None:
        assert listed.out == (
            f"Backlog (0)\nInProgress (1)\n  ST-0001  1/2 T  {TITLE}\nCompleted (0)\n"
        )


@NOT_YET
def test_status_on_main_lists_the_task_started_in_the_worktree(
    checkout: Path, tmp_path: Path
) -> None:
    fgraph(["start", "T-0002"], tmp_path / WORKTREE)
    assert fgraph(["status"], checkout).out.splitlines()[3] == "    => T-0002  a task title"
