"""The criterion of S-0129: driven by an agent, a work item is pulled only with a complexity.

The development is on with `driver = "agent"` and no `parallel`, and the record holds S-0001
with a Task and the complexity low and S-0002 with a Task and none, neither waiting. With the
driver left out the Tasks alone decide. Run end to end through `run` on a real git repository
in a temporary directory, never a faked git; the identity of its commits comes from the
environment and no git config is read.
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

XFAIL = pytest.mark.xfail(strict=True, reason="S-0129: the complexity is not asked yet")
NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
DRIVEN_BY_AN_AGENT = '[development]\nenabled = true\ndriver = "agent"\n'
DEVELOPMENT_ON = "[development]\nenabled = true\n"
NO_COMPLEXITY = (
    "fgraph: error: S-0002 has no complexity to start with: "
    "set it with fgraph amend S-0002 --complexity low, medium or high"
)
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def story(title: str, complexity: str | None = None) -> list[str]:
    """The command that adds the Story of that title, with that complexity when one is given."""
    held = [] if complexity is None else ["--complexity", complexity]
    return ["add", "story", title, *CRITERION, *held]


def task(parent: str) -> list[str]:
    """The command that adds a Task with a check to that work item."""
    return [
        "add",
        "task",
        "a task title",
        "--parent",
        parent,
        "--output",
        "an output",
        "--check",
        "make test",
    ]


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


def marked(out: str) -> list[str]:
    """The ids of the lines marked `>`, in the order written."""
    return [line.split()[1] for line in out.splitlines() if line.startswith("> ")]


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def checkout_with(tmp_path: Path, config: str) -> Path:
    """The checkout of main holding that config, S-0001 with low and S-0002 with no complexity."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text(config, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in (story("title 1", "low"), story("title 2"), task("S-0001"), task("S-0002")):
        fgraph(argv, path)
    return path


@pytest.fixture
def agent_checkout(tmp_path: Path) -> Path:
    """The checkout with the development driven by an agent."""
    return checkout_with(tmp_path, DRIVEN_BY_AN_AGENT)


@pytest.fixture
def developer_checkout(tmp_path: Path) -> Path:
    """The checkout with the development on and the driver left out."""
    return checkout_with(tmp_path, DEVELOPMENT_ON)


class TestStatusAsTextDrivenByAnAgent:
    def test_the_work_item_with_a_complexity_is_marked_alone(self, agent_checkout: Path) -> None:
        assert marked(fgraph(["status"], agent_checkout).out) == ["S-0001"]


class TestStatusAsJsonDrivenByAnAgent:
    def test_can_start_lists_the_work_item_with_a_complexity_alone(
        self, agent_checkout: Path
    ) -> None:
        document: dict[str, Any] = json.loads(
            fgraph(["status", "--format", "json"], agent_checkout).out
        )
        assert document["can_start"] == ["S-0001"]


class TestStatusAsTextDrivenByADeveloper:
    def test_both_work_items_are_marked(self, developer_checkout: Path) -> None:
        assert marked(fgraph(["status"], developer_checkout).out) == ["S-0001", "S-0002"]


class TestStatusAsJsonDrivenByADeveloper:
    def test_can_start_lists_both_work_items(self, developer_checkout: Path) -> None:
        document: dict[str, Any] = json.loads(
            fgraph(["status", "--format", "json"], developer_checkout).out
        )
        assert document["can_start"] == ["S-0001", "S-0002"]


@XFAIL
def test_a_start_with_no_complexity_is_refused_naming_it_and_the_amend(
    agent_checkout: Path,
) -> None:
    refused = fgraph(["start", "S-0002"], agent_checkout)
    assert (refused.status, refused.err.splitlines()[-1]) == (2, NO_COMPLEXITY)


def test_a_start_of_the_one_with_a_complexity_exits_with_zero(agent_checkout: Path) -> None:
    assert fgraph(["start", "S-0001"], agent_checkout).status == 0


def test_a_start_once_amended_with_a_complexity_exits_with_zero(agent_checkout: Path) -> None:
    fgraph(["amend", "S-0002", "--complexity", "medium"], agent_checkout)
    assert fgraph(["start", "S-0002"], agent_checkout).status == 0


@pytest.mark.parametrize("item", ["S-0001", "S-0002"])
def test_a_start_driven_by_a_developer_exits_with_zero(developer_checkout: Path, item: str) -> None:
    assert fgraph(["start", item], developer_checkout).status == 0
