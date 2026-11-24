"""Where a progress line is written with the development on: a started work item in its worktree.

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
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
NOTE_ITEM = ["note", "S-0001", "--progress", "the parser is read"]
NOTE_TASK = ["note", "T-0001", "--progress", "red: 1 failed"]


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
    try:
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
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
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


@pytest.fixture
def task_noted(worktree: Path) -> Outcome:
    """The progress line of T-0001 noted in the worktree, once the Task is started there."""
    fgraph(["start", "T-0001"], worktree)
    return fgraph(NOTE_TASK, worktree)


@pytest.mark.parametrize("argv", [NOTE_ITEM, NOTE_TASK], ids=["a-work-item", "a-task"])
def test_a_progress_line_noted_on_main_is_refused_naming_the_worktree(
    checkout: Path, worktree: Path, argv: list[str]
) -> None:
    outcome = fgraph(argv, checkout)
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


def test_a_progress_line_of_the_work_item_is_noted_and_committed_in_its_worktree(
    worktree: Path,
) -> None:
    outcome = fgraph(NOTE_ITEM, worktree)
    assert (outcome.status, outcome.out, git(worktree, "log", "-1", "--format=%s")) == (
        0,
        "noted S-0001\n",
        "chore: note S-0001 in the record",
    )


def test_a_progress_line_of_a_task_is_noted_and_committed_in_the_worktree(
    task_noted: Outcome, worktree: Path
) -> None:
    assert (task_noted.status, task_noted.out, git(worktree, "log", "-1", "--format=%s")) == (
        0,
        "noted T-0001 of S-0001\n",
        "chore: note T-0001 of S-0001 in the record",
    )


def test_the_commit_of_a_progress_line_holds_the_file_of_the_work_item_alone(
    task_noted: Outcome, worktree: Path
) -> None:
    shown = git(worktree, "show", "--name-only", "--format=", "HEAD")
    assert (task_noted.status, shown) == (0, ".fgraph/items/S-0001.toml")


def test_show_on_main_lists_the_line_of_the_task_noted_in_the_worktree(
    task_noted: Outcome, checkout: Path
) -> None:
    shown = fgraph(["show", "S-0001"], checkout)
    assert "    progress         2026-01-01  red: 1 failed\n" in shown.out


def test_a_progress_line_noted_from_main_on_the_record_of_the_worktree_is_written(
    checkout: Path, worktree: Path
) -> None:
    outcome = fgraph(["--dir", str(worktree / ".fgraph"), *NOTE_ITEM], checkout)
    assert (outcome.status, outcome.out) == (0, "noted S-0001\n")


def test_a_progress_line_of_a_work_item_in_backlog_is_noted_on_main(checkout: Path) -> None:
    fgraph(["add", "story", "another title", *CRITERION], checkout)
    outcome = fgraph(["note", "S-0002", "--progress", "a text"], checkout)
    assert (outcome.status, outcome.out) == (0, "noted S-0002\n")
