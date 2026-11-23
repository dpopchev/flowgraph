"""The criterion of S-0138 with the development on: a work item is blocked in its worktree.

The block is one commit of the branch of the work item; main lists it blocked, refuses the block
written there, counts it against development.parallel and refuses its landing. Run end to end
through `run` on a real git repository in a temporary directory, never a faked git; the
identity of its commits comes from the environment and no git config is read.
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
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
ADD_OTHER = ["add", "story", "another title", *CRITERION]


def task(parent: str) -> list[str]:
    """The command that adds a Task with a check to that work item."""
    return [
        *("add", "task", "a task title", "--parent", parent),
        *("--output", "an output", "--check", "make test"),
    ]


BLOCK = ["block", "S-0001", "--reason", "no key", "--waiting-on", "developer"]
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
STORY_FILE = ".fgraph/items/S-0001.toml"
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
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def turn_development_on(checkout: Path) -> None:
    """Commit the development on, one work item at once, as the config.toml of the record."""
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text(
        "[development]\nenabled = true\nparallel = 1\n", encoding="utf-8"
    )
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")


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
    """The checkout of main: S-0001 started on its worktree branch, S-0002 in Backlog."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    turn_development_on(path)
    for argv in (ADD_STORY, task("S-0001"), ADD_OTHER, task("S-0002"), ["start", "S-0001"]):
        fgraph(argv, path)
    return path


@pytest.fixture
def worktree(checkout: Path, tmp_path: Path) -> Path:
    """The worktree of the started Story."""
    return tmp_path / WORKTREE


@pytest.fixture
def blocked(worktree: Path) -> Outcome:
    """The block of S-0001 run in its worktree."""
    return fgraph(BLOCK, worktree)


def test_the_block_in_the_worktree_is_one_commit_of_its_branch_holding_its_file_alone(
    blocked: Outcome, worktree: Path
) -> None:
    assert (
        blocked.status,
        git(worktree, "log", "-1", "--format=%s"),
        git(worktree, "show", "--name-only", "--format=", "HEAD"),
    ) == (0, "chore: block S-0001 in the record", STORY_FILE)


def test_status_on_main_lists_it_blocked(blocked: Outcome, checkout: Path) -> None:
    assert f"! S-0001  0/1 T  {TITLE}  -- waiting on developer: no key" in (
        fgraph(["status"], checkout).out.splitlines()
    )


def test_the_block_on_main_is_refused_naming_the_worktree_and_writes_nothing(
    checkout: Path, worktree: Path
) -> None:
    outcome = fgraph(BLOCK, checkout)
    assert (
        outcome.status,
        outcome.err.splitlines()[-1:],
        git(checkout, "status", "--porcelain"),
    ) == (
        2,
        [f"fgraph: error: S-0001 is started: its Tasks are written in its worktree, {worktree}"],
        "",
    )


def test_a_start_beside_it_is_refused_under_development_parallel(
    blocked: Outcome, checkout: Path
) -> None:
    outcome = fgraph(["start", "S-0002"], checkout)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: S-0002 cannot start: development.parallel = 1, started already: S-0001"],
    )


def test_its_landing_is_refused_naming_the_block_and_merges_nothing(
    blocked: Outcome, checkout: Path
) -> None:
    outcome = fgraph(LAND, checkout)
    assert (
        outcome.status,
        outcome.err.splitlines()[-1:],
        git(checkout, "status", "--porcelain"),
        git(checkout, "branch", "--list", BRANCH),
    ) == (2, ["fgraph: error: S-0001 is blocked: unblock it first"], "", f"+ {BRANCH}")


def test_once_unblocked_in_its_worktree_with_its_task_completed_it_lands(
    blocked: Outcome, checkout: Path, worktree: Path
) -> None:
    fgraph(LAND, checkout)
    fgraph(["unblock", "S-0001"], worktree)
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    assert fgraph(LAND, checkout).status == 0
