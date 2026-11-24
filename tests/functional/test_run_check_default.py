"""The criterion of U-0023: a run() given no run_check refuses to run the check of a Task.

As the default of run_gate does, the default of run_check raises an AssertionError before anything
is written, so no run passes a check it did not run. Run end to end through `run` on a real git
repository in a temporary directory, never a faked git; each test gives its own runner, or none.
"""

import contextlib
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run
from flowgraph.development import RunGate

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
ON = "[development]\nenabled = true\n"
CHECK = "make test"
XFAIL = pytest.mark.xfail(
    strict=True, reason="U-0023: run() given no run_check passes every check without running it"
)
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


def fgraph(argv: Sequence[str], cwd: Path, runner: RunGate | None = None) -> Outcome:
    """Run the command in cwd with the runner of the check, or with none when runner is None."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    call = run if runner is None else partial(run, run_check=runner)
    status = call(
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


def complete(worktree: Path, runner: RunGate | None = None) -> Outcome:
    """Complete T-0001 in the worktree, at the commit its branch is on, given the runner."""
    head = git(worktree, "rev-parse", "HEAD")
    return fgraph(["complete", "T-0001", "--commit", head], worktree, runner)


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@XFAIL
def test_a_run_given_no_run_check_refuses_the_check_of_a_started_task(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, CHECK)
    with pytest.raises(
        AssertionError, match=r"^run\(\) was given no run_check to run 'make test' in "
    ):
        complete(worktree)


@XFAIL
def test_a_refused_complete_leaves_the_task_started(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, CHECK)
    with contextlib.suppress(AssertionError):
        complete(worktree)
    assert f"  S-0001  0/1 T  {TITLE}\n" in fgraph(["status"], worktree).out


@XFAIL
def test_a_refused_complete_writes_no_commit(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, CHECK)
    before = git(worktree, "rev-parse", "HEAD")
    with contextlib.suppress(AssertionError):
        complete(worktree)
    assert git(worktree, "rev-parse", "HEAD") == before


def test_a_run_given_a_passing_runner_completes_the_task_with_exit_zero(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, CHECK)
    assert complete(worktree, lambda command, directory: 0).status == 0


def test_a_run_given_a_runner_asks_it_the_command_once(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, CHECK)
    asked: list[str] = []

    def runner(command: str, directory: Path) -> int:
        asked.append(command)
        return 0

    complete(worktree, runner)
    assert asked == [CHECK]


def test_a_run_given_no_runner_completes_a_task_that_holds_no_check(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    fgraph(ADD_STORY, plain)
    fgraph(["add", "task", "a title", "--parent", "S-0001", "--output", "an output"], plain)
    fgraph(["start", "S-0001"], plain)
    fgraph(["start", "T-0001"], plain)
    completed = fgraph(["complete", "T-0001", "--commit", "abc1234"], plain)
    assert completed.status == 0
