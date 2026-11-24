"""The criterion of S-0098: fgraph status says that the branch of a started work item is old.

A record whose `config.toml` holds `[development] enabled = true` and `branch_max = "1d"`, and a
Story started two days before: its line in `fgraph status` and `fgraph watch` ends with `-- its
branch is older than 1d`, alone and under a Feature, and nothing is refused. Run end to end
through `run` on a real git repository in a temporary directory, never a faked git; the identity
of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

STARTED = datetime(2026, 1, 1, tzinfo=UTC)
ONE_DAY = STARTED + timedelta(days=1)
TWO_DAYS = STARTED + timedelta(days=2)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
DEVELOPMENT_ON = "[development]\nenabled = true\n"
AGED = '[development]\nenabled = true\nbranch_max = "1d"\n'
AGED_TRUNK = '[development]\nenabled = true\nmode = "trunk"\nbranch_max = "1d"\n'
NO_AGE = '[development]\nenabled = true\nbranch_max = "soon"\n'
WORDS = 'development.branch_max is "soon": it takes a whole number of days of 1 or more, as 1d'
PLAIN = "  S-0001  0/1 T  title 1"
OLD = PLAIN + "  -- its branch is older than 1d"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
XFAIL_SAID = pytest.mark.xfail(
    strict=True, reason="S-0098: status says nothing of the age of a branch"
)


def story(number: int, *parent: str) -> list[str]:
    """The command that adds the Story of that title, under the parent given."""
    return ["add", "story", f"title {number}", *CRITERION, *parent]


def task(parent: str) -> list[str]:
    """The command that adds a Task with a check to that work item."""
    output = ["--output", "an output", "--check", "make test"]
    return ["add", "task", "a task title", "--parent", parent, *output]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, at: datetime = STARTED) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on its files, the real git, at `at`."""
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
        now=lambda: at,
        open_git=open_git,
        load_config=read_config,
        run_check=lambda command, directory: 0,
    )
    return Outcome(status, "".join(out), "".join(err))


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


def started_under(tmp_path: Path, config: str | None) -> Path:
    """The repository of that config, S-0001 with its Task added and S-0001 started at STARTED."""
    path = init(tmp_path, config)
    for argv in (story(1), task("S-0001"), ["start", "S-0001"]):
        fgraph(argv, path)
    return path


def lines_of(outcome: Outcome) -> list[str]:
    """The lines of the output of the run."""
    return outcome.out.splitlines()


class TestTwoDaysAfterTheStart:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        return started_under(tmp_path, AGED)

    @XFAIL_SAID
    def test_status_says_the_branch_is_older_than_the_age(self, checkout: Path) -> None:
        assert OLD in lines_of(fgraph(["status"], checkout, TWO_DAYS))

    @XFAIL_SAID
    def test_watch_says_the_branch_is_older_than_the_age(self, checkout: Path) -> None:
        assert OLD in lines_of(fgraph(["watch", "--count", "1"], checkout, TWO_DAYS))

    def test_starting_a_task_in_the_worktree_is_not_refused(self, checkout: Path) -> None:
        listed = git(checkout, "worktree", "list", "--porcelain").splitlines()
        worktree = Path(next(line[9:] for line in listed[1:] if line.startswith("worktree ")))
        assert fgraph(["start", "T-0001"], worktree, TWO_DAYS).status == 0


class TestOneDayAfterTheStart:
    def test_status_says_nothing_at_the_age_exactly(self, tmp_path: Path) -> None:
        assert PLAIN in lines_of(fgraph(["status"], started_under(tmp_path, AGED), ONE_DAY))


class TestAStoryLeftInBacklog:
    def test_its_line_says_nothing_of_an_age(self, tmp_path: Path) -> None:
        path = started_under(tmp_path, AGED)
        fgraph(story(2), path)
        assert "  S-0002  title 2" in lines_of(fgraph(["status"], path, TWO_DAYS))


class TestAStoryUnderAFeature:
    @XFAIL_SAID
    def test_its_line_ends_with_the_word_two_columns_in(self, tmp_path: Path) -> None:
        path = init(tmp_path, AGED)
        add_feature = ["add", "feature", "a feature title", "--criterion", "a criterion"]
        for argv in (add_feature, story(1, "--parent", "F-0001"), task("S-0001")):
            fgraph(argv, path)
        fgraph(["start", "F-0001"], path)
        assert "    S-0001  0/1 T  title 1  -- its branch is older than 1d" in lines_of(
            fgraph(["status"], path, TWO_DAYS)
        )


class TestTheTrunk:
    def test_status_says_nothing_of_an_age(self, tmp_path: Path) -> None:
        assert PLAIN in lines_of(fgraph(["status"], started_under(tmp_path, AGED_TRUNK), TWO_DAYS))


class TestWithoutTheKey:
    def test_status_says_nothing_of_an_age(self, tmp_path: Path) -> None:
        assert PLAIN in lines_of(
            fgraph(["status"], started_under(tmp_path, DEVELOPMENT_ON), TWO_DAYS)
        )


class TestTheKey:
    def test_config_show_lists_the_age(self, tmp_path: Path) -> None:
        path = init(tmp_path, AGED)
        assert 'development.branch_max = "1d"' in lines_of(fgraph(["config", "show"], path))

    def test_config_show_lists_none_by_default(self, tmp_path: Path) -> None:
        path = init(tmp_path, DEVELOPMENT_ON)
        assert "development.branch_max = none" in lines_of(fgraph(["config", "show"], path))

    def test_config_set_writes_the_age(self, tmp_path: Path) -> None:
        path = init(tmp_path, DEVELOPMENT_ON)
        assert fgraph(["config", "set", "development.branch_max", "2d"], path) == Outcome(
            0, 'set development.branch_max = "2d"\n', ""
        )

    def test_a_value_that_is_no_age_is_refused(self, tmp_path: Path) -> None:
        path = init(tmp_path, NO_AGE)
        outcome = fgraph(["status"], path)
        assert (outcome.status, outcome.err.splitlines()[-1].endswith(WORDS)) == (2, True)
