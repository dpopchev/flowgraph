"""The criterion of the trunk: a work item is developed on main, with no branch and no worktree.

A record whose `config.toml` holds `[development] enabled = true` and `mode = "trunk"`. Run end
to end through `run` on a real git repository in a temporary directory, never a faked git; the
identity of its commits comes from the environment and no git config is read.
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
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", TITLE, *CRITERION]
ADD_TASK = [
    *("add", "task", "a task title", "--parent", "S-0001"),
    *("--output", "an output", "--check", "make test"),
]
ADD_SECOND_STORY = ["add", "story", "Raise the Tasks fgraph lists from 0 to 1", *CRITERION]
ADD_SECOND_TASK = [
    *("add", "task", "another task title", "--parent", "S-0002"),
    *("--output", "an output", "--check", "make test"),
]
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
DEVELOPMENT = "[development]\nenabled = true\n"
TRUNK = '[development]\nenabled = true\nmode = "trunk"\n'
LAND_REFUSED = (
    "fgraph: error: S-0001 cannot land: development.mode = trunk makes no branch to land"
    " -- complete it with fgraph complete S-0001 --commit SHA"
)
XFAIL_KEY = pytest.mark.xfail(
    strict=True, reason="S-0096: development.mode is no key of the configuration"
)
XFAIL_START = pytest.mark.xfail(strict=True, reason="S-0096: a start on the trunk makes a branch")


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
        run_check=lambda command, directory: 0,
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


def repository(tmp_path: Path, config: str) -> Path:
    """A git repository on main whose record holds that config.toml, committed."""
    path = tmp_path / "project"
    (path / ".fgraph").mkdir(parents=True)
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph" / "config.toml").write_text(config, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: configure the record")
    return path


def worked(checkout: Path) -> str:
    """Start the Story and its Task, commit work on main, complete the Task; the commit."""
    runs(checkout, ["start", "S-0001"], ["start", "T-0001"])
    (checkout / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(checkout, "add", "work.txt")
    git(checkout, "commit", "--quiet", "--message", "feat: do the work of the Task")
    sha = git(checkout, "rev-parse", "HEAD")
    fgraph(["complete", "T-0001", "--commit", sha], checkout)
    return sha


def last_error(outcome: Outcome) -> str:
    """The last line of what the run wrote as an error."""
    return outcome.err.splitlines()[-1]


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
    """A git repository on main, the trunk, and a Story with one Task."""
    path = repository(tmp_path, TRUNK)
    runs(path, ADD_STORY, ADD_TASK)
    return path


@XFAIL_START
class TestAStoryStartedOnTheTrunk:
    @pytest.fixture
    def started(self, checkout: Path) -> Outcome:
        return fgraph(["start", "S-0001"], checkout)

    def test_start_names_the_story_alone_and_writes_no_error(self, started: Outcome) -> None:
        assert started == Outcome(0, "started S-0001\n", "")

    def test_git_lists_main_as_the_one_branch(self, started: Outcome, checkout: Path) -> None:
        assert (started.status, git(checkout, "branch", "--format=%(refname:short)")) == (0, "main")

    def test_git_lists_one_work_tree(self, started: Outcome, checkout: Path) -> None:
        assert (
            started.status,
            git(checkout, "worktree", "list", "--porcelain").count("worktree "),
        ) == (0, 1)


@XFAIL_START
class TestAStoryWorkedAndCompletedOnTheTrunk:
    @pytest.fixture
    def done(self, checkout: Path) -> tuple[Outcome, str]:
        sha = worked(checkout)
        return fgraph(["complete", "S-0001", "--commit", sha], checkout), sha

    def test_complete_names_the_story_and_the_commit_of_main(
        self, done: tuple[Outcome, str]
    ) -> None:
        outcome, sha = done
        assert outcome == Outcome(0, f"completed S-0001 at {sha}\n", "")

    def test_status_lists_the_story_completed_at_that_commit(
        self, done: tuple[Outcome, str], checkout: Path
    ) -> None:
        _, sha = done
        assert f"  S-0001  {sha}  {TITLE}" in fgraph(["status"], checkout).out.splitlines()

    def test_the_completion_is_the_commit_of_main(
        self, done: tuple[Outcome, str], checkout: Path
    ) -> None:
        assert git(checkout, "log", "-1", "--format=%s", "main") == (
            "chore: complete S-0001 in the record"
        )

    def test_git_lists_main_as_the_one_branch_and_one_work_tree(
        self, done: tuple[Outcome, str], checkout: Path
    ) -> None:
        assert (
            done[0].status,
            git(checkout, "branch", "--format=%(refname:short)"),
            git(checkout, "worktree", "list", "--porcelain").count("worktree "),
        ) == (0, "main", 1)


@XFAIL_START
def test_land_exits_with_two_naming_the_key(checkout: Path) -> None:
    worked(checkout)
    refused = fgraph(["land", "S-0001", "--message", "feat: land"], checkout)
    assert (refused.status, last_error(refused)) == (2, LAND_REFUSED)


@XFAIL_START
def test_land_moves_nothing_on_main(checkout: Path) -> None:
    worked(checkout)
    before = git(checkout, "rev-parse", "main")
    refused = fgraph(["land", "S-0001", "--message", "feat: land"], checkout)
    assert (last_error(refused), git(checkout, "rev-parse", "main")) == (LAND_REFUSED, before)


@XFAIL_START
def test_a_feature_started_on_the_trunk_names_its_first_story(checkout: Path) -> None:
    started = runs(
        checkout,
        ["add", "feature", "a feature title", "--criterion", "a criterion"],
        ["add", "story", "another title", *CRITERION, "--parent", "F-0001"],
        ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"],
        ["start", "F-0001"],
    )
    assert started == Outcome(0, "started F-0001 with S-0002\n", "")


@XFAIL_START
def test_a_branch_of_the_story_that_is_there_does_not_refuse_the_start(checkout: Path) -> None:
    git(checkout, "branch", "wi/S-0001-raise-the-stories-fgraph")
    assert fgraph(["start", "S-0001"], checkout) == Outcome(0, "started S-0001\n", "")


@XFAIL_KEY
def test_a_second_story_is_not_started_beside_the_first(checkout: Path) -> None:
    refused = runs(
        checkout, ADD_SECOND_STORY, ADD_SECOND_TASK, ["start", "S-0001"], ["start", "S-0002"]
    )
    assert (refused.status, last_error(refused)) == (
        2,
        "fgraph: error: S-0002 cannot start: development.parallel = 1, started already: S-0001",
    )


@XFAIL_KEY
def test_config_show_lists_the_mode_after_the_parallel_limit(checkout: Path) -> None:
    lines = fgraph(["config", "show"], checkout).out.splitlines()
    keys = ("development.parallel", "development.mode")
    assert [line for line in lines if line.startswith(keys)] == [
        "development.parallel = 1",
        'development.mode = "trunk"',
    ]


@XFAIL_KEY
def test_config_set_writes_the_mode(tmp_path: Path) -> None:
    path = repository(tmp_path, DEVELOPMENT)
    assert fgraph(["config", "set", "development.mode", "trunk"], path) == Outcome(
        0, 'set development.mode = "trunk"\n', ""
    )


@XFAIL_KEY
def test_a_parallel_limit_above_one_beside_the_trunk_is_refused(tmp_path: Path) -> None:
    path = repository(tmp_path, f"{TRUNK}parallel = 2\n")
    refused = fgraph(["status"], path)
    ending = (
        "development.parallel is 2 while development.mode is trunk:"
        " the trunk holds one started work item at a time"
    )
    assert (refused.status, last_error(refused).endswith(ending)) == (2, True)


def test_a_start_with_the_mode_left_out_makes_its_branch(tmp_path: Path) -> None:
    path = repository(tmp_path, DEVELOPMENT)
    started = runs(path, ADD_STORY, ADD_TASK, ["start", "S-0001"])
    assert started.out.splitlines()[1].startswith("branch wi/S-0001-")
