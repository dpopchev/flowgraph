"""The start of a work item while its branch is there: refused before anything is written.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read. The start
takes over no branch that is there: the developer deletes it or gives another slug.
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
ADD_ALONE = ["add", "story", "a title that stands alone", *CRITERION]
TASK_FOR_ALONE = [
    "add",
    "task",
    "a task title",
    "--parent",
    "S-0001",
    "--output",
    "an output",
    "--check",
    "make test",
]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists", *CRITERION, "--parent", "F-0001"]
ADD_TASK = [
    "add",
    "task",
    "a task title",
    "--parent",
    "S-0002",
    "--output",
    "an output",
    "--check",
    "make test",
]
ADDED = (ADD_ALONE, TASK_FOR_ALONE, ADD_FEATURE, ADD_STORY, ADD_TASK)
DEVELOPMENT_ON = "[development]\nenabled = true\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
STORY_BRANCH = "wi/S-0001-a-title-that-stands"
FIRST_BRANCH = "wi/S-0002-raise-the-stories-fgraph"
LAST_ADD = "chore: add T-0002 of S-0002 in the record"
THERE = (
    "fgraph: error: {} cannot start: the branch {} is there already"
    " -- delete it or give another --slug"
)
BACKLOG_LINE = "  bucket       Backlog"
XFAIL = pytest.mark.xfail(
    strict=True, reason="B-0027: the start is committed before git refuses the branch"
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


def checkout_under(path: Path, config: str) -> Path:
    """A git repository on main at the path under that config.toml, its commits holding ADDED.

    S-0001 stands alone and F-0001 holds S-0002, each Story in Backlog with one Task.
    """
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    record = path / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text(config, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in ADDED:
        fgraph(argv, path)
    return path


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def refusal(outcome: Outcome) -> tuple[int, str]:
    """The exit status of the run and the last line of its error output."""
    return (outcome.status, outcome.err.splitlines()[-1])


class TestAStoryStartedWhileItsBranchIsThere:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = checkout_under(tmp_path / "project", DEVELOPMENT_ON)
        git(path, "branch", STORY_BRANCH)
        return path

    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        return fgraph(["start", "S-0001"], checkout)

    def test_start_exits_with_two_naming_the_branch(self, refused: Outcome) -> None:
        assert refusal(refused) == (2, THERE.format("S-0001", STORY_BRANCH))

    def test_nothing_is_written_and_no_commit_is_made(
        self, refused: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "status", "--porcelain"),
            git(checkout, "log", "-1", "--format=%s", "main"),
        ) == ("", LAST_ADD)

    def test_the_story_stays_in_backlog(self, refused: Outcome, checkout: Path) -> None:
        assert fgraph(["show", "S-0001"], checkout).out.splitlines()[1] == BACKLOG_LINE

    def test_the_story_starts_once_the_branch_is_deleted(
        self, refused: Outcome, checkout: Path, tmp_path: Path
    ) -> None:
        git(checkout, "branch", "-D", STORY_BRANCH)
        started = fgraph(["start", "S-0001"], checkout)
        worktree = tmp_path / "project.worktrees" / "S-0001-a-title-that-stands"
        assert (started.status, started.out) == (
            0,
            f"started S-0001\nbranch {STORY_BRANCH} in {worktree}\n",
        )

    def test_the_story_starts_under_another_slug(
        self, refused: Outcome, checkout: Path, tmp_path: Path
    ) -> None:
        started = fgraph(["start", "S-0001", "--slug", "another"], checkout)
        worktree = tmp_path / "project.worktrees" / "S-0001-another"
        assert (started.status, started.out) == (
            0,
            f"started S-0001\nbranch wi/S-0001-another in {worktree}\n",
        )


def test_a_story_started_under_a_slug_whose_branch_is_there_is_refused_naming_it(
    tmp_path: Path,
) -> None:
    checkout = checkout_under(tmp_path / "project", DEVELOPMENT_ON)
    git(checkout, "branch", "wi/S-0001-a-slug")
    refused = fgraph(["start", "S-0001", "--slug", "a-slug"], checkout)
    assert refusal(refused) == (2, THERE.format("S-0001", "wi/S-0001-a-slug"))


def test_a_story_started_twice_is_refused_in_its_own_words(tmp_path: Path) -> None:
    checkout = checkout_under(tmp_path / "project", DEVELOPMENT_ON)
    fgraph(["start", "S-0001"], checkout)
    again = fgraph(["start", "S-0001"], checkout)
    assert refusal(again) == (2, "fgraph: error: S-0001 is started already")


class TestAFeatureStartedWhileTheBranchItWouldMakeIsThere:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = checkout_under(tmp_path / "project", DEVELOPMENT_ON)
        git(path, "branch", FIRST_BRANCH)
        return path

    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        return fgraph(["start", "F-0001"], checkout)

    @XFAIL
    def test_start_exits_with_two_naming_the_branch(self, refused: Outcome) -> None:
        assert refusal(refused) == (2, THERE.format("F-0001", FIRST_BRANCH))

    @XFAIL
    def test_nothing_is_written_and_no_commit_is_made(
        self, refused: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "status", "--porcelain"),
            git(checkout, "log", "-1", "--format=%s", "main"),
        ) == ("", LAST_ADD)

    @XFAIL
    def test_the_feature_stays_in_backlog(self, refused: Outcome, checkout: Path) -> None:
        assert fgraph(["show", "F-0001"], checkout).out.splitlines()[1] == BACKLOG_LINE

    @XFAIL
    def test_the_feature_starts_once_the_branch_is_deleted(
        self, refused: Outcome, checkout: Path, tmp_path: Path
    ) -> None:
        git(checkout, "branch", "-D", FIRST_BRANCH)
        started = fgraph(["start", "F-0001"], checkout)
        worktree = tmp_path / "project.worktrees" / "S-0002-raise-the-stories-fgraph"
        assert (started.status, started.out) == (
            0,
            f"started F-0001 with S-0002\nbranch {FIRST_BRANCH} in {worktree}\n",
        )


@XFAIL
def test_a_feature_started_under_a_slug_whose_branch_is_there_is_refused_naming_it(
    tmp_path: Path,
) -> None:
    checkout = checkout_under(tmp_path / "project", DEVELOPMENT_ON)
    git(checkout, "branch", "wi/S-0002-a-slug")
    refused = fgraph(["start", "F-0001", "--slug", "a-slug"], checkout)
    assert refusal(refused) == (2, THERE.format("F-0001", "wi/S-0002-a-slug"))
