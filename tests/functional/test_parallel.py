"""The criterion of parallel: a Story started beside as many as `[development] parallel` is refused.

The record turns the development on with `parallel = 1` and holds a started Story. Run end to
end through `run` on a real git repository in a temporary directory, never a faked git; the
identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0044: development.parallel is no key yet"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
ONE_AT_ONCE = "[development]\nenabled = true\nparallel = 1\n"
REFUSAL = "S-0002 cannot start: development.parallel = 1, started already: S-0001"
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
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def limit_to_one(checkout: Path) -> None:
    """Commit the config.toml of the record of the checkout: the development on, parallel = 1."""
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text(ONE_AT_ONCE, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: start one work item at once")


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
    """The checkout of main under parallel = 1: S-0001 started, S-0002 in Backlog with a Task."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    limit_to_one(path)
    for argv in (ADD_STORY, ADD_OTHER, ADD_TASK, TASK_FOR_OTHER, ["start", "S-0001"]):
        fgraph(argv, path)
    return path


class TestASecondStoryStartedBesideAStartedOneUnderParallelOne:
    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        return fgraph(["start", "S-0002"], checkout)

    def test_start_exits_with_two_naming_the_started_story(self, refused: Outcome) -> None:
        assert (refused.status, refused.err.splitlines()[-1:]) == (2, [f"fgraph: error: {REFUSAL}"])

    def test_nothing_is_written_after_the_start_of_the_first_story(
        self, refused: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "status", "--porcelain"),
            git(checkout, "log", "-1", "--format=%s", "main"),
        ) == ("", "chore: start S-0001 in the record")

    def test_the_branch_of_the_first_story_is_the_one_branch_of_a_work_item(
        self, refused: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "branch", "--list", "--format=%(refname:short)", "wi/*") == BRANCH
