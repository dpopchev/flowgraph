"""The criterion of B-0036: of two starts of one work item at one time, one is refused.

Run through `run` on a real git repository, one start after the other, the refusal of a second
start naming the agent that holds the work item. Then two fgraph start as real processes at one
time on a git repository with the development on, the lock of B-0035 holding the second back.
"""

import json
import os
import subprocess
import sys
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
AGENT_LINE = "  agent        sonnet-a1\n"
REFUSED = "fgraph: error: S-0001 is started already"
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
        run_check=lambda command, directory: 0,
    )
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def last_error(outcome: Outcome) -> str:
    """The last line of the error output of the run."""
    return outcome.err.splitlines()[-1]


def git(cwd: Path, environment: dict[str, str], *args: str) -> str:
    """The output of the git command run in cwd with that environment; fails on a non-zero exit."""
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=environment, check=True, capture_output=True, text=True
    )
    return done.stdout


def make_repository(root: Path, environment: dict[str, str]) -> Path:
    """A git repository on main whose first commit holds the config.toml, the development on."""
    path = root / "project"
    path.mkdir()
    git(path, environment, "init", "--quiet", "--initial-branch", "main")
    record = path / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(path, environment, "add", ".fgraph/config.toml")
    git(path, environment, "commit", "--quiet", "--message", "chore: turn the development on")
    return path


def git_environment(root: Path) -> dict[str, str]:
    """The environment of git: the identity and no git config of the machine."""
    empty = root / "gitconfig"
    empty.touch()
    return {
        **os.environ,
        **IDENTITY,
        "GIT_CONFIG_GLOBAL": str(empty),
        "GIT_CONFIG_NOSYSTEM": "1",
    }


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in git_environment(tmp_path).items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """The repository on main whose commits hold a Story in Backlog with one Task."""
    path = make_repository(tmp_path, git_environment(tmp_path))
    runs(path, ADD_STORY, ADD_TASK)
    return path


class TestASecondStartOfAWorkItemAnAgentHolds:
    @pytest.fixture
    def second(self, checkout: Path) -> Outcome:
        return runs(
            checkout,
            ["start", "S-0001", "--agent", "sonnet-a1"],
            ["start", "S-0001", "--agent", "opus-b2"],
        )

    def test_is_refused_naming_the_agent_that_holds_it(self, second: Outcome) -> None:
        assert (second.status, last_error(second)) == (
            2,
            "fgraph: error: S-0001 is started already: sonnet-a1 holds it",
        )

    def test_leaves_the_agent_that_holds_it(self, second: Outcome, checkout: Path) -> None:
        assert AGENT_LINE in fgraph(["show", "S-0001"], checkout).out


def test_a_second_start_of_a_work_item_no_agent_holds_is_refused(checkout: Path) -> None:
    second = runs(checkout, ["start", "S-0001"], ["start", "S-0001", "--agent", "opus-b2"])
    assert (second.status, last_error(second)) == (2, REFUSED)


@dataclass(frozen=True)
class Processes:
    """Two fgraph start at one time as processes: the repository, the environment, the runs."""

    repository: Path
    environment: dict[str, str]
    outcomes: dict[str, Outcome]

    @property
    def winner(self) -> str:
        """The agent of the process that exited 0."""
        return next(name for name, each in self.outcomes.items() if each.status == 0)

    @property
    def loser(self) -> Outcome:
        """The run of the process that did not exit 0."""
        return next(each for each in self.outcomes.values() if each.status != 0)


def finished(process: subprocess.Popen[str]) -> Outcome:
    """What the process left once it has exited."""
    out, err = process.communicate()
    return Outcome(process.returncode, out, err)


@pytest.fixture(scope="module")
def processes(tmp_path_factory: pytest.TempPathFactory) -> Processes:
    """Two fgraph start of S-0001 with --agent a and --agent b started together, waited for."""
    root = tmp_path_factory.mktemp("root")
    environment = git_environment(root)
    repository = make_repository(root, environment)
    for argv in (ADD_STORY, ADD_TASK):
        subprocess.run(
            [sys.executable, "-m", "flowgraph.cli", *argv],
            cwd=repository,
            env=environment,
            check=True,
            capture_output=True,
        )
    started = {
        name: subprocess.Popen(
            [sys.executable, "-m", "flowgraph.cli", "start", "S-0001", "--agent", name],
            cwd=repository,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for name in ("a", "b")
    }
    return Processes(
        repository, environment, {name: finished(each) for name, each in started.items()}
    )


def agent_of(processes: Processes) -> Any:
    """The agent of S-0001 in the JSON of status, indexed so that its absence raises."""
    out = subprocess.run(
        [sys.executable, "-m", "flowgraph.cli", "status", "--format", "json"],
        cwd=processes.repository,
        env=processes.environment,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    document = json.loads(out)
    found = next(i for b in document["buckets"] for i in b["items"] if i["id"] == "S-0001")
    return found["agent"]


class TestTwoStartsAtOneTimeAsProcesses:
    def test_the_exit_statuses_are_zero_and_two(self, processes: Processes) -> None:
        assert sorted(each.status for each in processes.outcomes.values()) == [0, 2]

    def test_the_refusal_names_the_agent_whose_start_was_taken(self, processes: Processes) -> None:
        assert last_error(processes.loser) == (
            f"fgraph: error: S-0001 is started already: {processes.winner} holds it"
        )

    def test_git_status_is_empty(self, processes: Processes) -> None:
        assert git(processes.repository, processes.environment, "status", "--porcelain") == ""

    def test_status_lists_the_agent_whose_start_was_taken(self, processes: Processes) -> None:
        assert agent_of(processes) == processes.winner

    def test_git_log_holds_one_commit_of_the_start(self, processes: Processes) -> None:
        logged = git(processes.repository, processes.environment, "log", "--format=%s")
        assert logged.splitlines().count("chore: start S-0001 in the record") == 1
