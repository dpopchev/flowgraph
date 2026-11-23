"""The criterion of S-0117: one command prints the /goal line of a Feature for a developer to paste.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Iterator, Sequence
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
RECORD = [
    ["add", "feature", "the first feature", "--criterion", "a criterion"],
    ["add", "story", "the first story", *CRITERION, "--parent", "F-0001"],
    ["add", "story", "the second story", *CRITERION, "--parent", "F-0001"],
    ["add", "story", "the third story", *CRITERION, "--parent", "F-0001"],
    ["add", "feature", "the second feature", "--criterion", "a criterion"],
]
ENABLED = ["config", "set", "development.enabled", "true"]
PARALLEL = ["config", "set", "development.parallel", "3"]
DRIVER = ["config", "set", "development.driver", "agent"]
LINE = (
    "/goal Develop F-0001 until fgraph show F-0001 lists S-0001, S-0002 and S-0003 Completed, "
    "or stop after 8 hours. This session is the coordinator: it hands each whole work item to "
    "one subagent, at most 3 at once as development.parallel says. The goal is met as well when "
    "this session prints [HALT] <id>: <the decision needed> on a change to a criterion, a Task "
    "or the scope of a work item, or a removal, that the developer has not agreed.\n"
)


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


@pytest.fixture(scope="module")
def environment(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A directory to make the repositories in, the identity of git set from the environment."""
    base = tmp_path_factory.mktemp("goal").resolve()
    empty = base / "gitconfig"
    empty.touch()
    with pytest.MonkeyPatch.context() as variables:
        for name, value in IDENTITY.items():
            variables.setenv(name, value)
        variables.setenv("GIT_CONFIG_GLOBAL", str(empty))
        variables.setenv("GIT_CONFIG_NOSYSTEM", "1")
        yield base


def checkout(base: Path, name: str, *settings: list[str]) -> Path:
    """A repository on main whose record holds F-0001 with three Stories and an empty F-0002."""
    path = base / name
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    git(path, "commit", "--quiet", "--allow-empty", "--message", "chore: start the project")
    for argv in [*RECORD, *settings]:
        made = fgraph(argv, path)
        assert made.status == 0, f"{' '.join(argv)}: {made.err}"
    return path


@pytest.fixture(scope="module")
def driven_by_agent(environment: Path) -> Path:
    """A record with the development on, development.parallel 3 and the driver an agent."""
    return checkout(environment, "agent", ENABLED, PARALLEL, DRIVER)


@pytest.fixture(scope="module")
def driven_by_developer(environment: Path) -> Path:
    """A record with the development on and the driver left out, so a developer drives."""
    return checkout(environment, "developer", ENABLED, PARALLEL)


@pytest.fixture(scope="module")
def development_off(environment: Path) -> Path:
    """A record with the development off."""
    return checkout(environment, "off")


def goal(path: Path, *argv: str) -> Outcome:
    """The outcome of fgraph goal with the arguments, run in the checkout."""
    return fgraph(["goal", *argv], path)


class TestTheGoalOfAFeature:
    @pytest.fixture
    def printed(self, driven_by_agent: Path) -> Outcome:
        return goal(driven_by_agent, "F-0001")

    def test_it_exits_with_zero(self, printed: Outcome) -> None:
        assert printed.status == 0

    def test_it_prints_exactly_one_newline(self, printed: Outcome) -> None:
        assert printed.out.count("\n") == 1

    def test_it_ends_the_line_with_that_newline(self, printed: Outcome) -> None:
        assert printed.out.endswith("\n")

    def test_it_prints_the_line_with_the_bound_of_8_hours(self, printed: Outcome) -> None:
        assert printed.out == LINE

    def test_the_line_is_under_4000_characters(self, printed: Outcome) -> None:
        assert 0 < len(printed.out) < 4000

    def test_it_bounds_the_goal_by_the_hours_asked(self, driven_by_agent: Path) -> None:
        assert goal(driven_by_agent, "F-0001", "--hours", "4").out == LINE.replace("8", "4", 1)


class TestTheGoalRefused:
    def test_a_driver_left_out_is_refused_naming_development_driver(
        self, driven_by_developer: Path
    ) -> None:
        assert "development.driver" in goal(driven_by_developer, "F-0001").err

    def test_a_development_off_is_refused_naming_development_enabled(
        self, development_off: Path
    ) -> None:
        assert "development.enabled" in goal(development_off, "F-0001").err

    def test_a_feature_with_no_work_item_is_refused_saying_it_holds_none_in_backlog(
        self, driven_by_agent: Path
    ) -> None:
        assert "F-0002 holds no work item in Backlog" in goal(driven_by_agent, "F-0002").err

    def test_hours_of_0_are_refused_saying_a_whole_number_of_1_or_more(
        self, driven_by_agent: Path
    ) -> None:
        assert "a whole number of 1 or more" in goal(driven_by_agent, "F-0001", "--hours", "0").err
