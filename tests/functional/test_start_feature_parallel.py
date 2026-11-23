"""The criterion of S-0111: the Stories of a started Feature start side by side, up to parallel.

The record turns the development on with `parallel = 3` and holds a Feature started with the
first of its four Stories, each with a Task. Run end to end through `run` on a real git
repository in a temporary directory, never a faked git; the identity of its commits comes from
the environment and no git config is read.
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
    pytest.mark.xfail(strict=True, reason="S-0111: a Feature still starts one work item at a time"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
TITLES = ("alpha story", "beta story", "gamma story", "delta story")
THREE_AT_ONCE = "[development]\nenabled = true\nparallel = 3\n"
BRANCHES = {
    "S-0001": "wi/S-0001-alpha-story",
    "S-0002": "wi/S-0002-beta-story",
    "S-0003": "wi/S-0003-gamma-story",
}
REFUSAL = "S-0004 cannot start: development.parallel = 3, started already: S-0001, S-0002, S-0003"
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


def story_with_task(number: int) -> list[list[str]]:
    """The commands that add the Story of that number under F-0001 and one Task of it."""
    story = ["add", "story", TITLES[number - 1], *CRITERION, "--parent", "F-0001"]
    task = [
        "add",
        "task",
        "a task title",
        "--parent",
        f"S-000{number}",
        "--output",
        "an output",
        "--check",
        "make test",
    ]
    return [story, task]


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
    """The checkout of main under parallel = 3: F-0001 started with S-0001, three in Backlog."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    record = path / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text(THREE_AT_ONCE, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: start three work items at once")
    stories = [argv for number in range(1, 5) for argv in story_with_task(number)]
    for argv in (ADD_FEATURE, *stories, ["start", "F-0001"]):
        fgraph(argv, path)
    return path


class TestTheStoriesOfAStartedFeatureStartedSideBySideUnderParallelThree:
    @pytest.fixture
    def second(self, checkout: Path) -> Outcome:
        return fgraph(["start", "S-0002"], checkout)

    @pytest.fixture
    def third(self, checkout: Path, second: Outcome) -> Outcome:
        return fgraph(["start", "S-0003"], checkout)

    @pytest.fixture
    def fourth(self, checkout: Path, third: Outcome) -> Outcome:
        return fgraph(["start", "S-0004"], checkout)

    def test_start_of_the_second_exits_with_zero_naming_its_branch(self, second: Outcome) -> None:
        assert (second.status, second.out.splitlines()[0]) == (0, "started S-0002")

    def test_start_of_the_third_exits_with_zero_naming_its_branch(self, third: Outcome) -> None:
        assert (third.status, third.out.splitlines()[0]) == (0, "started S-0003")

    def test_the_branch_of_the_second_is_named_in_its_output(self, second: Outcome) -> None:
        assert second.out.splitlines()[1].startswith(f"branch {BRANCHES['S-0002']} in ")

    def test_the_branch_of_the_third_is_named_in_its_output(self, third: Outcome) -> None:
        assert third.out.splitlines()[1].startswith(f"branch {BRANCHES['S-0003']} in ")

    def test_each_branch_is_at_the_commit_of_its_start(
        self, checkout: Path, third: Outcome
    ) -> None:
        assert git(checkout, "rev-parse", BRANCHES["S-0003"]) == git(checkout, "rev-parse", "main")

    def test_each_worktree_has_its_branch_checked_out(
        self, checkout: Path, tmp_path: Path, third: Outcome
    ) -> None:
        worktrees = tmp_path / "project.worktrees"
        assert [
            git(worktrees / branch.removeprefix("wi/"), "branch", "--show-current")
            for branch in BRANCHES.values()
        ] == list(BRANCHES.values())

    def test_start_of_the_fourth_exits_with_two_naming_development_parallel_and_the_three_started(
        self, fourth: Outcome
    ) -> None:
        assert (fourth.status, fourth.err.splitlines()[-1]) == (2, f"fgraph: error: {REFUSAL}")
