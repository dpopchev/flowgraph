"""The commit of a set of the configuration: `fgraph config set` is a write as any other.

It is committed alone, left uncommitted when the configuration it leaves turns the commits off,
and refused on the branch of a work item. Run end to end through `run` on a real git repository
in a temporary directory, never a faked git; the identity of its commits comes from the
environment and no git config is read.
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
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
ADD_TASK = [
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
SET_ENABLED = ["config", "set", "development.enabled", "true"]
SET_PARALLEL = ["config", "set", "development.parallel", "2"]
CONFIG = ".fgraph/config.toml"
ENABLED = "[development]\nenabled = true\n"
UNCOMMITTED = "[git]\ncommit = false\n"
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
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


def changes(cwd: Path) -> str:
    """What git status lists in cwd, untracked files one by one; its first line is not stripped."""
    done = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.rstrip()


def repository(tmp_path: Path, config: str | None) -> Path:
    """A git repository on main with one commit, `first`, that holds `README`.

    The commit holds that config.toml of the record too, unless there is none.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / "README").write_text("a project\n", encoding="utf-8")
    git(path, "add", "README")
    if config is not None:
        (path / ".fgraph").mkdir()
        (path / CONFIG).write_text(config, encoding="utf-8")
        git(path, "add", CONFIG)
    git(path, "commit", "--quiet", "--message", "first")
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


class TestAKeySetOnARecordWithoutAConfigFile:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = repository(tmp_path, None)
        fgraph(SET_ENABLED, path)
        return path

    def test_the_set_is_committed_under_the_key(self, checkout: Path) -> None:
        assert git(checkout, "log", "--format=%s") == (
            "chore: set development.enabled in the record\nfirst"
        )

    def test_the_commit_holds_the_config_file_alone(self, checkout: Path) -> None:
        assert git(checkout, "show", "--name-only", "--format=") == CONFIG

    def test_nothing_is_left_uncommitted(self, checkout: Path) -> None:
        assert changes(checkout) == ""


def test_a_key_set_to_the_value_the_file_writes_makes_no_commit(tmp_path: Path) -> None:
    checkout = repository(tmp_path, ENABLED)
    outcome = fgraph(SET_ENABLED, checkout)
    assert (outcome, git(checkout, "log", "--format=%s")) == (
        Outcome(0, "set development.enabled = true\n", ""),
        "first",
    )


class TestAKeySetWithTheCommitsOff:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = repository(tmp_path, UNCOMMITTED)
        fgraph(["config", "set", "development.merge", "squash"], path)
        return path

    def test_git_log_holds_no_new_commit(self, checkout: Path) -> None:
        assert git(checkout, "log", "--format=%s") == "first"

    def test_the_config_file_is_left_changed(self, checkout: Path) -> None:
        assert changes(checkout) == f" M {CONFIG}"


class TestTheCommitsTurnedOffByASet:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = repository(tmp_path, None)
        fgraph(["config", "set", "git.commit", "false"], path)
        return path

    def test_git_log_holds_no_new_commit(self, checkout: Path) -> None:
        assert git(checkout, "log", "--format=%s") == "first"

    def test_the_config_file_is_left_uncommitted(self, checkout: Path) -> None:
        assert changes(checkout) == f"?? {CONFIG}"


class TestTheCommitsTurnedOnByASet:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = repository(tmp_path, UNCOMMITTED)
        fgraph(["config", "set", "git.commit", "true"], path)
        return path

    def test_the_set_is_committed_under_the_key(self, checkout: Path) -> None:
        assert git(checkout, "log", "--format=%s") == "chore: set git.commit in the record\nfirst"

    def test_nothing_is_left_uncommitted(self, checkout: Path) -> None:
        assert changes(checkout) == ""


class TestAKeySetOnTheBranchOfAStartedStory:
    @pytest.fixture
    def branch(self, tmp_path: Path) -> Path:
        """The worktree of the branch of a started Story, the development on."""
        checkout = repository(tmp_path, ENABLED)
        for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"]):
            fgraph(argv, checkout)
        return tmp_path / WORKTREE

    @pytest.fixture
    def refused(self, branch: Path) -> Outcome:
        return fgraph(SET_PARALLEL, branch)

    def test_set_exits_with_two_naming_the_story_the_branch_owns(self, refused: Outcome) -> None:
        assert (refused.status, refused.err.splitlines()[-1:]) == (
            2,
            [
                "fgraph: error: the configuration is not set here:"
                f" the branch {BRANCH} writes S-0001 alone"
            ],
        )

    def test_nothing_is_written_on_the_branch(self, refused: Outcome, branch: Path) -> None:
        assert (changes(branch), git(branch, "log", "-1", "--format=%s")) == (
            "",
            "chore: start S-0001 in the record",
        )

    def test_show_lists_the_configuration_on_the_branch(self, branch: Path) -> None:
        assert fgraph(["config", "show"], branch).out.splitlines()[1] == (
            "development.enabled = true"
        )
