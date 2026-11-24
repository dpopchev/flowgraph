"""The criterion of S-0144, with the development on: where the amend of a Task is written.

In the worktree of a started work item, as one commit of its branch; on main it is refused naming
that worktree. Run end to end through `run` on a real git repository in a temporary directory,
never a faked git; the identity of its commits comes from the environment, no git config is read.
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
ADD_OTHER = ["add", "story", "another title", *CRITERION]
AMEND_SECOND = ["amend", "T-0002", "--title", "a new title"]
AMEND_THIRD = ["amend", "T-0003", "--title", "a new title"]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
STORY_FILE = ".fgraph/items/S-0001.toml"
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}


def task(parent: str) -> list[str]:
    """The command that adds a Task with a check to that work item."""
    return [
        *("add", "task", "a task title", "--parent", parent),
        *("--output", "an output", "--check", "make test"),
    ]


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
            run_check=lambda command, directory: 0,
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def turn_development_on(checkout: Path) -> None:
    """Commit `[development] enabled = true` as the config.toml of the record of the checkout."""
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")


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
    """The checkout of main: S-0001 with T-0001 and T-0002 started, S-0002 with T-0003."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    turn_development_on(path)
    adds = (ADD_STORY, task("S-0001"), task("S-0001"), ADD_OTHER, task("S-0002"))
    for argv in (*adds, ["start", "S-0001"]):
        fgraph(argv, path)
    return path


@pytest.fixture
def worktree(checkout: Path, tmp_path: Path) -> Path:
    """The worktree of the started Story."""
    return tmp_path / WORKTREE


def test_the_amend_in_the_worktree_is_one_commit_of_its_branch_holding_its_file_alone(
    worktree: Path,
) -> None:
    outcome = fgraph(AMEND_SECOND, worktree)
    assert (
        outcome.status,
        outcome.out,
        git(worktree, "log", "-1", "--format=%s"),
        git(worktree, "show", "--name-only", "--format=", "HEAD"),
    ) == (
        0,
        "amended T-0002 of S-0001\n",
        "chore: amend T-0002 of S-0001 in the record",
        STORY_FILE,
    )


class TestTheAmendOfATaskOfAStartedWorkItemOnMain:
    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        return fgraph(AMEND_SECOND, checkout)

    def test_it_is_refused_naming_the_worktree(self, refused: Outcome, worktree: Path) -> None:
        assert (refused.status, refused.err.splitlines()[-1:]) == (
            2,
            [
                "fgraph: error: S-0001 is started: its Tasks are written in its worktree,"
                f" {worktree}"
            ],
        )

    def test_nothing_is_written_on_main(
        self, refused: Outcome, checkout: Path, worktree: Path
    ) -> None:
        assert (
            refused.err.splitlines()[-1:],
            git(checkout, "status", "--porcelain"),
            git(checkout, "log", "-1", "--format=%s"),
        ) == (
            [
                "fgraph: error: S-0001 is started: its Tasks are written in its worktree,"
                f" {worktree}"
            ],
            "",
            "chore: start S-0001 in the record",
        )


def test_the_amend_on_main_of_a_task_of_a_work_item_in_backlog_is_written(checkout: Path) -> None:
    outcome = fgraph(AMEND_THIRD, checkout)
    assert (outcome.status, outcome.out, git(checkout, "log", "-1", "--format=%s")) == (
        0,
        "amended T-0003 of S-0002\n",
        "chore: amend T-0003 of S-0002 in the record",
    )


def test_the_amend_in_the_worktree_of_a_task_of_another_work_item_is_refused(
    worktree: Path,
) -> None:
    outcome = fgraph(AMEND_THIRD, worktree)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        [f"fgraph: error: S-0002 is not written here: the branch {BRANCH} writes S-0001 alone"],
    )
