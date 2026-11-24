"""The expected of B-0031: fgraph goal refuses a Feature holding a work item in Backlog not planned.

A work item with no Task, or with no complexity while the development is driven by an agent, is
refused in the words of the start of the Feature, the first such work item in start order named.
Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read. The red
tests are strict xfails until the goal is wired; the guards pass before and after.
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
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
DRIVEN_BY_AN_AGENT = '[development]\nenabled = true\ndriver = "agent"\n'
DEVELOPMENT_ON = "[development]\nenabled = true\n"
FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer sees it"]
NO_TASK_LINE = "fgraph: error: F-0001 cannot start: S-0002 has no Task to start with"
NO_TASK_OF_S0003 = "fgraph: error: F-0001 cannot start: S-0003 has no Task to start with"
NO_COMPLEXITY_LINE = (
    "fgraph: error: F-0001 cannot start: S-0002 has no complexity to start with: "
    "set it with fgraph amend S-0002 --complexity low, medium or high"
)
GOAL_START = "/goal Develop F-0001 until fgraph show F-0001 lists S-0001 and S-0002 Completed,"
XFAIL = pytest.mark.xfail(
    strict=True, reason="B-0031: fgraph goal words a line over work items no start takes"
)


def story(title: str, complexity: str | None = None) -> list[str]:
    """The command that adds the Story of that title, with that complexity when one is given."""
    held = [] if complexity is None else ["--complexity", complexity]
    return ["add", "story", title, *CRITERION, "--parent", "F-0001", *held]


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


NO_TASK = [
    story("title 1", "low"),
    story("title 2", "medium"),
    story("title 3", "high"),
    task("S-0001"),
]
NO_COMPLEXITY = [
    story("title 1", "low"),
    story("title 2"),
    story("title 3"),
    task("S-0001"),
    task("S-0002"),
    task("S-0003"),
]
MIXED = [story("title 1"), story("title 2", "low"), task("S-0001")]
PLANNED = [story("title 1", "low"), story("title 2", "medium"), task("S-0001"), task("S-0002")]


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


def goal(path: Path, *argv: str) -> Outcome:
    """The outcome of fgraph goal with the arguments, run in the checkout."""
    return fgraph(["goal", *argv], path)


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


def checkout_with(tmp_path: Path, config: str, commands: Sequence[Sequence[str]]) -> Path:
    """A checkout of main holding that config, F-0001 and then each command, all of them exit 0."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text(config, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in [FEATURE, *commands]:
        made = fgraph(argv, path)
        assert made.status == 0, f"{' '.join(argv)}: {made.err}"
    return path


@pytest.fixture
def no_task(tmp_path: Path) -> Path:
    """Driven by an agent: S-0002 and S-0003 hold no Task."""
    return checkout_with(tmp_path, DRIVEN_BY_AN_AGENT, NO_TASK)


@pytest.fixture
def no_complexity(tmp_path: Path) -> Path:
    """Driven by an agent: S-0002 and S-0003 hold a Task and no complexity."""
    return checkout_with(tmp_path, DRIVEN_BY_AN_AGENT, NO_COMPLEXITY)


@pytest.fixture
def mixed(tmp_path: Path) -> Path:
    """Driven by an agent: S-0001 lacks a complexity and S-0002 a Task."""
    return checkout_with(tmp_path, DRIVEN_BY_AN_AGENT, MIXED)


@pytest.fixture
def planned(tmp_path: Path) -> Path:
    """Driven by an agent: every work item in Backlog holds a Task and a complexity."""
    return checkout_with(tmp_path, DRIVEN_BY_AN_AGENT, PLANNED)


@pytest.fixture
def developer_no_task(tmp_path: Path) -> Path:
    """Developer-driven: the driver is left out and S-0002 holds no Task."""
    return checkout_with(tmp_path, DEVELOPMENT_ON, NO_TASK)


class TestGoalOfAPlannedFeature:
    def test_a_planned_feature_exits_with_zero(self, planned: Path) -> None:
        assert goal(planned, "F-0001").status == 0

    def test_a_planned_feature_is_worded_as_before(self, planned: Path) -> None:
        assert goal(planned, "F-0001").out.startswith(GOAL_START)


class TestGoalOfAFeatureNotPlanned:
    @XFAIL
    def test_no_task_exits_with_two(self, no_task: Path) -> None:
        refused = goal(no_task, "F-0001")
        assert (refused.status, refused.err.splitlines()[-1]) == (2, NO_TASK_LINE)

    @XFAIL
    def test_no_task_prints_nothing(self, no_task: Path) -> None:
        assert goal(no_task, "F-0001").out == ""

    @XFAIL
    def test_no_complexity_exits_with_two(self, no_complexity: Path) -> None:
        refused = goal(no_complexity, "F-0001")
        assert (refused.status, refused.err.splitlines()[-1]) == (2, NO_COMPLEXITY_LINE)

    @XFAIL
    def test_a_missing_task_is_named_before_a_missing_complexity(self, mixed: Path) -> None:
        refused = goal(mixed, "F-0001")
        assert (refused.status, refused.err.splitlines()[-1]) == (2, NO_TASK_LINE)

    @XFAIL
    def test_the_first_missing_task_in_the_queue_order_is_named(self, no_task: Path) -> None:
        fgraph(["reorder", "S-0003", "--before", "S-0002"], no_task)
        refused = goal(no_task, "F-0001")
        assert (refused.status, refused.err.splitlines()[-1]) == (2, NO_TASK_OF_S0003)

    @XFAIL
    def test_the_last_error_line_is_the_one_of_the_start(self, no_complexity: Path) -> None:
        started = fgraph(["start", "F-0001"], no_complexity)
        refused = goal(no_complexity, "F-0001")
        assert refused.err.splitlines()[-1:] == started.err.splitlines()[-1:]


class TestGoalRefusedBeforeThePlan:
    def test_a_driver_left_out_is_named_before_the_plan(self, developer_no_task: Path) -> None:
        assert "development.driver" in goal(developer_no_task, "F-0001").err.splitlines()[-1]
