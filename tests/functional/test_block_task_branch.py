"""The criterion of the block and the unblock of a Task of a started Story: made in its worktree.

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
ADD_TASK = [
    "add",
    "task",
    "a task title",
    "--parent",
    "S-0001",
    "--output",
    "an output",
    "--check",
    "make test",
]
START_TASK = ["start", "T-0001"]
BLOCK = ["block", "T-0001", "--reason", "no key", "--waiting-on", "developer"]
UNBLOCK = ["unblock", "T-0001"]
BLOCK_ADDED = ["block", "T-0002", "--reason", "no key", "--waiting-on", "developer"]
UNBLOCK_ADDED = ["unblock", "T-0002"]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
RED = pytest.mark.xfail(
    strict=True,
    reason="B-0032: the block and the unblock of a Task on main answer from the copy of main",
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
    """The checkout of main: S-0001 with one Task, started on its worktree branch."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    turn_development_on(path)
    for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"]):
        fgraph(argv, path)
    return path


@pytest.fixture
def worktree(checkout: Path, tmp_path: Path) -> Path:
    """The worktree of the started Story."""
    return tmp_path / WORKTREE


@pytest.mark.parametrize(
    ("setup", "command"),
    [
        pytest.param((START_TASK, BLOCK), UNBLOCK, marks=RED, id="unblock-of-one-blocked-there"),
        pytest.param((START_TASK, BLOCK), BLOCK, marks=RED, id="block-of-one-blocked-there"),
        pytest.param((START_TASK,), BLOCK, marks=RED, id="block-of-one-started-there"),
        pytest.param((START_TASK,), UNBLOCK, marks=RED, id="unblock-of-one-started-there"),
        pytest.param((), BLOCK, marks=RED, id="block-of-one-in-backlog"),
        pytest.param((), UNBLOCK, marks=RED, id="unblock-of-one-in-backlog"),
        pytest.param((ADD_TASK,), BLOCK_ADDED, marks=RED, id="block-of-one-added-there"),
        pytest.param((ADD_TASK,), UNBLOCK_ADDED, marks=RED, id="unblock-of-one-added-there"),
    ],
)
def test_a_block_or_an_unblock_of_a_task_on_main_is_refused_naming_the_worktree_and_writes_nothing(
    checkout: Path,
    worktree: Path,
    setup: Sequence[Sequence[str]],
    command: Sequence[str],
) -> None:
    for argv in setup:
        fgraph(argv, worktree)
    outcome = fgraph(command, checkout)
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


def test_a_block_of_a_task_started_in_its_worktree_is_written(
    checkout: Path, worktree: Path
) -> None:
    fgraph(START_TASK, worktree)
    outcome = fgraph(BLOCK, worktree)
    assert (outcome.status, outcome.out) == (0, "blocked T-0001 of S-0001\n")


def test_a_block_in_its_worktree_is_committed_there(checkout: Path, worktree: Path) -> None:
    fgraph(START_TASK, worktree)
    fgraph(BLOCK, worktree)
    assert (
        git(worktree, "log", "-1", "--format=%s") == "chore: block T-0001 of S-0001 in the record"
    )


def test_an_unblock_of_a_task_blocked_in_its_worktree_is_written(
    checkout: Path, worktree: Path
) -> None:
    fgraph(START_TASK, worktree)
    fgraph(BLOCK, worktree)
    outcome = fgraph(UNBLOCK, worktree)
    assert (outcome.status, outcome.out) == (0, "unblocked T-0001 of S-0001\n")


def test_an_unblock_in_its_worktree_is_committed_there(checkout: Path, worktree: Path) -> None:
    fgraph(START_TASK, worktree)
    fgraph(BLOCK, worktree)
    fgraph(UNBLOCK, worktree)
    assert git(worktree, "log", "-1", "--format=%s") == (
        "chore: unblock T-0001 of S-0001 in the record"
    )


def test_a_block_with_the_dir_of_the_worktree_record_is_written(
    checkout: Path, worktree: Path
) -> None:
    fgraph(START_TASK, worktree)
    outcome = fgraph(["--dir", str(worktree / ".fgraph"), *BLOCK], checkout)
    assert (outcome.status, outcome.out) == (0, "blocked T-0001 of S-0001\n")


def test_a_start_block_and_unblock_on_main_without_a_worktree_are_written(
    checkout: Path, worktree: Path
) -> None:
    git(checkout, "worktree", "remove", str(worktree))
    outcomes = tuple(fgraph(argv, checkout).out for argv in (START_TASK, BLOCK, UNBLOCK))
    assert outcomes == (
        "started T-0001 of S-0001\n",
        "blocked T-0001 of S-0001\n",
        "unblocked T-0001 of S-0001\n",
    )


def test_a_blocked_task_in_its_worktree_shows_in_the_status_of_main(
    checkout: Path, worktree: Path
) -> None:
    fgraph(START_TASK, worktree)
    fgraph(BLOCK, worktree)
    lines = fgraph(["status"], checkout).out.splitlines()
    assert "    !  T-0001  a task title  -- waiting on developer: no key" in lines


def test_an_unblock_of_a_story_blocked_in_its_worktree_on_main_says_it_is_not_blocked(
    checkout: Path, worktree: Path
) -> None:
    fgraph(["block", "S-0001", "--reason", "no key", "--waiting-on", "developer"], worktree)
    outcome = fgraph(["unblock", "S-0001"], checkout)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: S-0001 is not blocked"],
    )
