"""The criterion of S-0113: a start names the agent its work item is handed to, listed after.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import json
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = [
    *("add", "story", TITLE),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
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
START = ["start", "S-0001", "--agent", "sonnet-a1"]
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}

red_exit = pytest.mark.xfail(strict=True, reason="S-0113: start takes no --agent yet")
red_show = pytest.mark.xfail(strict=True, reason="S-0113: show lists no agent yet")
red_status = pytest.mark.xfail(strict=True, reason="S-0113: status lists no agent yet")


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


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def enable_development(project: Path) -> None:
    """Write `[development] enabled = true` as the config.toml of the record of the project."""
    record = project / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")


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
    """A git repository on main whose commits hold a Story in Backlog with one Task.

    Its first commit holds the config.toml of the record, which turns the development on.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    enable_development(path)
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    runs(path, ADD_STORY, ADD_TASK)
    return path


def listed(checkout: Path) -> list[str]:
    """The lines status prints for S-0001, as printed."""
    out = fgraph(["status"], checkout).out
    return [line for line in out.splitlines() if line.startswith("  S-0001")]


def agent_of(checkout: Path) -> Any:
    """The agent of S-0001 in the JSON of status, indexed so that its absence raises."""
    document = json.loads(fgraph(["status", "--format", "json"], checkout).out)
    found = next(i for b in document["buckets"] for i in b["items"] if i["id"] == "S-0001")
    return found["agent"]


class TestAStoryStartedWithAnAgent:
    @pytest.fixture
    def started(self, checkout: Path) -> Outcome:
        return fgraph(START, checkout)

    @red_exit
    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    @red_status
    def test_status_lists_the_agent_between_the_progress_and_the_title(
        self, started: Outcome, checkout: Path
    ) -> None:
        assert listed(checkout) == [f"  S-0001  0/1 T  [sonnet-a1]  {TITLE}"]

    @red_show
    def test_show_lists_the_agent(self, started: Outcome, checkout: Path) -> None:
        assert "  agent        sonnet-a1\n" in fgraph(["show", "S-0001"], checkout).out

    @red_status
    def test_the_json_of_status_holds_the_agent(self, started: Outcome, checkout: Path) -> None:
        assert agent_of(checkout) == "sonnet-a1"
