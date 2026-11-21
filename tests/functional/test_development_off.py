"""The criterion of the development off: a start is committed on main and makes no branch.

A record that holds no `config.toml` has the development off. Run end to end through `run` on a
real git repository in a temporary directory, never a faked git; the identity of its commits
comes from the environment and no git config is read.
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
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = [
    *("add", "story", TITLE),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
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


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


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
    """A git repository on main whose record holds no config.toml, and a Story with one Task."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    runs(path, ADD_STORY, ADD_TASK)
    return path


class TestAStoryStartedInARecordWithNoConfig:
    @pytest.fixture
    def started(self, checkout: Path) -> Outcome:
        return fgraph(["start", "S-0001"], checkout)

    def test_start_names_the_story_alone_and_writes_no_error(self, started: Outcome) -> None:
        assert started == Outcome(0, "started S-0001\n", "")

    def test_the_start_is_the_commit_of_main_the_one_branch(
        self, started: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "branch", "--format=%(refname:short) %(subject)") == (
            "main chore: start S-0001 in the record"
        )

    def test_git_lists_no_branch_of_a_work_item(self, started: Outcome, checkout: Path) -> None:
        assert git(checkout, "branch", "--list", "--format=%(refname:short)", "wi/*") == ""

    def test_git_lists_no_new_worktree(self, started: Outcome, checkout: Path) -> None:
        assert git(checkout, "worktree", "list", "--porcelain").count("worktree ") == 1


def test_a_start_outside_a_git_work_tree_warns_of_nothing(tmp_path: Path) -> None:
    assert runs(tmp_path, ADD_STORY, ADD_TASK, ["start", "S-0001"]).err == ""


class TestAStoryLandedInARecordWithNoConfig:
    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        return runs(
            checkout,
            ["start", "S-0001"],
            ["start", "T-0001"],
            ["complete", "T-0001", "--commit", "abc1234"],
            ["land", "S-0001", "--message", "feat: land the first Story"],
        )

    def test_land_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_land_names_the_key_that_turns_the_development_on(
        self, refused: Outcome, checkout: Path
    ) -> None:
        assert refused.err.splitlines()[-1] == (
            "fgraph: error: S-0001 cannot land: the development is off"
            f" -- set development.enabled = true in {checkout / '.fgraph' / 'config.toml'}"
        )
