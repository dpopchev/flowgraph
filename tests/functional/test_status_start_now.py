"""The criterion of S-0110: fgraph status marks every work item that can start now.

The record turns the development on with `parallel = 3` and holds S-0001 started, S-0002 to
S-0005 in Backlog, each with a Task, S-0002 waiting for S-0004. The limit leaves two places, so
S-0003 and S-0004 are marked `>`, and S-0005 is left out by the limit, not by a dependency. Run
end to end through `run` on a real git repository in a temporary directory, never a faked git;
the identity of its commits comes from the environment and no git config is read.
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
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
THREE_AT_ONCE = "[development]\nenabled = true\nparallel = 3\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
RED = "S-0110: fgraph status marks only the next to start so far"


def story(number: int) -> list[str]:
    """The command that adds the Story of that title."""
    return ["add", "story", f"title {number}", *CRITERION]


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


RECORD = [
    *(story(number) for number in range(1, 6)),
    *(task(f"S-000{number}") for number in range(1, 6)),
    ["amend", "S-0002", "--depends-on", "S-0004"],
    ["start", "S-0001"],
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


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """The checkout of main under parallel = 3 holding RECORD."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text(THREE_AT_ONCE, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: start three work items at once")
    for argv in RECORD:
        fgraph(argv, path)
    return path


class TestStatusAsText:
    @pytest.fixture
    def printed(self, checkout: Path) -> Outcome:
        return fgraph(["status"], checkout)

    def test_status_exits_with_zero(self, printed: Outcome) -> None:
        assert printed.status == 0

    @pytest.mark.xfail(strict=True, reason=RED)
    def test_the_two_places_the_limit_leaves_are_marked(self, printed: Outcome) -> None:
        assert marked(printed.out) == ["S-0003", "S-0004"]

    def test_the_story_that_waits_is_marked_with_a_tilde(self, printed: Outcome) -> None:
        assert [line for line in printed.out.splitlines() if "S-0002" in line][0][0] == "~"


class TestStatusAsJson:
    @pytest.fixture
    def document(self, checkout: Path) -> dict[str, Any]:
        return json.loads(fgraph(["status", "--format", "json"], checkout).out)

    @pytest.fixture
    def exit_status(self, checkout: Path) -> int:
        return fgraph(["status", "--format", "json"], checkout).status

    def test_status_exits_with_zero(self, exit_status: int) -> None:
        assert exit_status == 0

    @pytest.mark.xfail(strict=True, reason=RED)
    def test_can_start_lists_the_two_places_the_limit_leaves(
        self, document: dict[str, Any]
    ) -> None:
        assert document["can_start"] == ["S-0003", "S-0004"]

    def test_next_to_start_is_the_first_of_them(self, document: dict[str, Any]) -> None:
        assert document["next_to_start"] == "S-0003"


class TestWatchOneFrame:
    @pytest.fixture
    def watched(self, checkout: Path) -> Outcome:
        return fgraph(["watch", "--count", "1"], checkout)

    def test_watch_exits_with_zero(self, watched: Outcome) -> None:
        assert watched.status == 0

    @pytest.mark.xfail(strict=True, reason=RED)
    def test_the_two_places_the_limit_leaves_are_marked(self, watched: Outcome) -> None:
        assert marked(watched.out) == ["S-0003", "S-0004"]
