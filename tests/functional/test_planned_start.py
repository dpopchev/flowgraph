"""The criterion of S-0127: an item of the Backlog is marked and started only once planned.

The development is on with no `parallel`, and the record holds S-0001 alone with no Task,
S-0002 alone with a Task, F-0001 with no work item, F-0002 with S-0003 planned and S-0004
without a Task, and F-0003 with S-0005 and S-0006 each planned. Run end to end through `run`
on a real git repository in a temporary directory, never a faked git; the identity of its
commits comes from the environment and no git config is read.
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
DEVELOPMENT_ON = "[development]\nenabled = true\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def story(title: str, parent: str | None = None) -> list[str]:
    """The command that adds the Story of that title, under that Feature when one is given."""
    under = [] if parent is None else ["--parent", parent]
    return ["add", "story", title, *CRITERION, *under]


def feature(title: str) -> list[str]:
    """The command that adds the Feature of that title."""
    return ["add", "feature", title, "--criterion", "a developer sees it"]


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
    story("title 1"),
    story("title 2"),
    task("S-0002"),
    feature("feature 1"),
    feature("feature 2"),
    story("title 3", "F-0002"),
    story("title 4", "F-0002"),
    task("S-0003"),
    feature("feature 3"),
    story("title 5", "F-0003"),
    story("title 6", "F-0003"),
    task("S-0005"),
    task("S-0006"),
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
    """The checkout of main with the development on, parallel left out, holding RECORD."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text(DEVELOPMENT_ON, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in RECORD:
        fgraph(argv, path)
    return path


class TestStatusAsText:
    def test_the_planned_work_item_and_the_planned_feature_are_marked_alone(
        self, checkout: Path
    ) -> None:
        assert marked(fgraph(["status", "--backlog"], checkout).out) == ["S-0002", "F-0003"]


class TestStatusAsJson:
    @pytest.fixture
    def document(self, checkout: Path) -> dict[str, Any]:
        return json.loads(fgraph(["status", "--format", "json"], checkout).out)

    def test_can_start_lists_the_planned_work_item_and_the_planned_feature(
        self, document: dict[str, Any]
    ) -> None:
        assert document["can_start"] == ["S-0002", "F-0003"]

    def test_next_to_start_is_the_planned_work_item(self, document: dict[str, Any]) -> None:
        assert document["next_to_start"] == "S-0002"


@pytest.mark.parametrize(
    ("item", "message"),
    [
        ("S-0001", "fgraph: error: S-0001 has no Task to start with"),
        ("F-0001", "fgraph: error: F-0001 has no work item in Backlog to start with"),
        ("F-0002", "fgraph: error: F-0002 cannot start: S-0004 has no Task to start with"),
    ],
)
def test_a_start_refused_exits_with_two_and_names_what_it_lacks(
    checkout: Path, item: str, message: str
) -> None:
    refused = fgraph(["start", item], checkout)
    assert (refused.status, refused.err.splitlines()[-1]) == (2, message)


@pytest.mark.parametrize("item", ["S-0002", "F-0003"])
def test_a_start_of_one_planned_whole_exits_with_zero(checkout: Path, item: str) -> None:
    assert fgraph(["start", item], checkout).status == 0
