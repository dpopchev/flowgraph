"""The criterion of S-0115: the key development.driver is set and shown by fgraph config.

The record of a development with the key left out or set to an agent works as before: a Story
is added without a complexity and started without an agent. Run end to end through `run` on
the files of a record in a temporary directory, and on a real git repository for the guards.
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
SET_AGENT = ["config", "set", "development.driver", "agent"]
SHOW = ["config", "show"]
CONFIG = Path(".fgraph") / "config.toml"
ENABLED = "[development]\nenabled = true\n"
ADD_STORY = [
    *("add", "story", "Raise the Stories fgraph lists from 0 to 1"),
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
START_PLAIN = ["start", "S-0001"]
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
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: NOW,
        load_config=read_config,
    )
    return Outcome(status, "".join(out), "".join(err))


def fgraph_in_git(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on its files and the real git."""
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


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A directory whose record holds a config.toml that turns the development on."""
    (tmp_path / ".fgraph").mkdir()
    (tmp_path / CONFIG).write_text(ENABLED, encoding="utf-8")
    return tmp_path


class TestTheDriverSetToAnAgentOnARecordWithTheDevelopmentOn:
    @pytest.fixture
    def set_agent(self, project: Path) -> Outcome:
        return fgraph(SET_AGENT, project)

    def test_set_exits_with_zero(self, set_agent: Outcome) -> None:
        assert set_agent.status == 0

    def test_show_then_lists_the_driver_as_agent_in_quotes(
        self, set_agent: Outcome, project: Path
    ) -> None:
        assert 'development.driver = "agent"' in fgraph(SHOW, project).out.splitlines()


class TestTheDriverLeftOutOfARecordWithTheDevelopmentOn:
    def test_show_lists_the_driver_as_developer_in_quotes(self, project: Path) -> None:
        assert 'development.driver = "developer"' in fgraph(SHOW, project).out.splitlines()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """A git repository on main whose first commit holds the config.toml of the record.

    The config turns the development on and leaves the driver out.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    (path / CONFIG).write_text(ENABLED, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    return path


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


class TestAStoryAddedAndStartedOnARecordLeavingTheDriverOut:
    def test_add_without_a_complexity_exits_with_zero(self, repository: Path) -> None:
        assert fgraph_in_git(ADD_STORY, repository).status == 0

    def test_start_without_an_agent_exits_with_zero(self, repository: Path) -> None:
        fgraph_in_git(ADD_STORY, repository)
        fgraph_in_git(ADD_TASK, repository)
        assert fgraph_in_git(START_PLAIN, repository).status == 0
