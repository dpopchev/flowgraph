"""The criterion of S-0114: fgraph status marks a started work item whose Tasks are all completed.

The record turns the development on and holds S-0001 started with its one Task completed and
S-0002 started with one Task completed and one in Backlog, each Task completed in the worktree of
its branch. Status and watch mark `?` the line of the first, not that of the second, and the JSON
lists the first under `ready_for_review`. With the development off the same mark is shown. Run
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
DEVELOPMENT_ON = "[development]\nenabled = true\n"
READY = "? S-0001  1/1 T  title 1"
NOT_READY = "  S-0002  1/2 T  title 2"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def story(number: int) -> list[str]:
    """The command that adds the Story of that title."""
    return ["add", "story", f"title {number}", *CRITERION]


def task(parent: str, *, checked: bool = True) -> list[str]:
    """The command that adds a Task to that work item, with a check while the development is on."""
    check = ["--check", "make test"] if checked else []
    return ["add", "task", "a task title", "--parent", parent, "--output", "an output", *check]


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


def worktree_of(started: Outcome) -> Path:
    """The path of the worktree a start printed, on its last line after `in `."""
    return Path(started.out.splitlines()[-1].rpartition(" in ")[2])


def complete_in(worktree: Path, task_id: str) -> None:
    """Start the Task in the worktree, commit a file there and complete the Task at that commit."""
    fgraph(["start", task_id], worktree)
    (worktree / f"{task_id}.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", f"{task_id}.txt")
    git(worktree, "commit", "--quiet", "--message", f"feat: do {task_id}")
    fgraph(["complete", task_id, "--commit", git(worktree, "rev-parse", "HEAD")], worktree)


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def init(tmp_path: Path, config: str | None) -> Path:
    """A git repository of main holding the config.toml given, none when config is None."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "keep").touch()
    if config is not None:
        (path / ".fgraph" / "config.toml").write_text(config, encoding="utf-8")
    git(path, "add", ".fgraph")
    git(path, "commit", "--quiet", "--message", "chore: start the record")
    return path


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """The checkout of main under the development, S-0001 ready for review and S-0002 not."""
    path = init(tmp_path, DEVELOPMENT_ON)
    for argv in (story(1), story(2), task("S-0001"), task("S-0002"), task("S-0002")):
        fgraph(argv, path)
    first = fgraph(["start", "S-0001", "--slug", "first"], path)
    second = fgraph(["start", "S-0002", "--slug", "second"], path)
    complete_in(worktree_of(first), "T-0001")
    complete_in(worktree_of(second), "T-0002")
    return path


@pytest.fixture
def checkout_off(tmp_path: Path) -> Path:
    """The checkout of main without a config.toml, S-0001 started with its Task completed."""
    path = init(tmp_path, None)
    for argv in (story(1), task("S-0001", checked=False), ["start", "S-0001"], ["start", "T-0001"]):
        fgraph(argv, path)
    fgraph(["complete", "T-0001", "--commit", "abc1234"], path)
    return path


class TestStatusAsText:
    @pytest.fixture
    def printed(self, checkout: Path) -> Outcome:
        return fgraph(["status"], checkout)

    def test_status_exits_with_zero(self, printed: Outcome) -> None:
        assert printed.status == 0

    @pytest.mark.xfail(strict=True, reason="S-0114: the mark ? is not written yet")
    def test_the_work_item_whose_tasks_are_completed_is_marked(self, printed: Outcome) -> None:
        assert READY in printed.out.splitlines()

    def test_the_work_item_with_a_task_in_backlog_is_not_marked(self, printed: Outcome) -> None:
        assert NOT_READY in printed.out.splitlines()


class TestStatusAsJson:
    @pytest.fixture
    def printed(self, checkout: Path) -> Outcome:
        return fgraph(["status", "--format", "json"], checkout)

    @pytest.fixture
    def document(self, printed: Outcome) -> dict[str, Any]:
        return json.loads(printed.out)

    def test_status_exits_with_zero(self, printed: Outcome) -> None:
        assert printed.status == 0

    @pytest.mark.xfail(strict=True, reason="S-0114: ready_for_review is not in the document yet")
    def test_ready_for_review_lists_the_work_item_alone(self, document: dict[str, Any]) -> None:
        assert document["ready_for_review"] == ["S-0001"]

    def test_the_progress_of_the_first_is_read_from_its_worktree(
        self, document: dict[str, Any]
    ) -> None:
        in_progress = next(b for b in document["buckets"] if b["name"] == "InProgress")
        first = next(item for item in in_progress["items"] if item["id"] == "S-0001")
        assert first["progress"] == {"completed": 1, "total": 1}


class TestWatchOneFrame:
    @pytest.fixture
    def watched(self, checkout: Path) -> Outcome:
        return fgraph(["watch", "--count", "1"], checkout)

    def test_watch_exits_with_zero(self, watched: Outcome) -> None:
        assert watched.status == 0

    @pytest.mark.xfail(strict=True, reason="S-0114: the mark ? is not written yet")
    def test_the_work_item_whose_tasks_are_completed_is_marked(self, watched: Outcome) -> None:
        assert READY in watched.out.splitlines()


class TestStatusWithTheDevelopmentOff:
    @pytest.fixture
    def printed(self, checkout_off: Path) -> Outcome:
        return fgraph(["status"], checkout_off)

    def test_status_exits_with_zero(self, printed: Outcome) -> None:
        assert printed.status == 0

    @pytest.mark.xfail(strict=True, reason="S-0114: the mark ? is not written yet")
    def test_the_work_item_whose_tasks_are_completed_on_main_is_marked(
        self, printed: Outcome
    ) -> None:
        assert READY in printed.out.splitlines()
