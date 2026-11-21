"""The criterion of the scope of a branch: on the branch of a Story fgraph writes that Story alone.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, run

pytestmark = pytest.mark.functional

# What the branch refuses once ST-0010 lands; what it still writes is stated without the mark.
NOT_YET = pytest.mark.xfail(strict=True, reason="ST-0010: a branch writes every work item file")

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_THIRD = ["add", "story", "a third title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "ST-0002", "--output", "an output"]
BRANCH = "wi/ST-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "ST-0001-raise-the-stories-fgraph"
ALONE = f"the branch {BRANCH} writes ST-0001 alone"
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
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def refusal(outcome: Outcome) -> tuple[int, list[str]]:
    """The exit status of a run and the last line of its error output."""
    return outcome.status, outcome.err.splitlines()[-1:]


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
    """The checkout of main: ST-0001 started on its worktree branch, two Stories in Backlog."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    for argv in (ADD_STORY, ADD_OTHER, ADD_THIRD, ADD_TASK, ["start", "ST-0001"]):
        fgraph(argv, path)
    return path


@pytest.fixture
def branch(checkout: Path, tmp_path: Path) -> Path:
    """The worktree of the branch of the started Story."""
    return tmp_path / WORKTREE


@NOT_YET
class TestATaskAddedToAnotherStoryOnTheBranchOfAStartedStory:
    @pytest.fixture
    def refused(self, branch: Path) -> Outcome:
        return fgraph(TASK_FOR_OTHER, branch)

    def test_add_task_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_add_task_names_the_story_the_branch_owns(self, refused: Outcome) -> None:
        assert refused.err.splitlines()[-1:] == [
            f"fgraph: error: ST-0002 is not written here: {ALONE}"
        ]

    def test_nothing_is_written_on_the_branch(self, refused: Outcome, branch: Path) -> None:
        assert (git(branch, "status", "--porcelain"), git(branch, "log", "-1", "--format=%s")) == (
            "",
            "chore: start ST-0001 in the record",
        )


def test_a_task_added_to_its_own_story_on_the_branch_is_written(branch: Path) -> None:
    outcome = fgraph(ADD_TASK, branch)
    assert (outcome.status, outcome.out) == (0, "added T-0002 to ST-0001\n")


@NOT_YET
def test_a_story_added_on_the_branch_is_refused(branch: Path) -> None:
    assert refusal(fgraph(ADD_STORY, branch)) == (
        2,
        [f"fgraph: error: ST-0004 is not written here: {ALONE}"],
    )


@NOT_YET
def test_a_reorder_on_the_branch_is_refused(branch: Path) -> None:
    assert refusal(fgraph(["reorder", "ST-0003", "--before", "ST-0002"], branch)) == (
        2,
        [f"fgraph: error: the Backlog is not reordered here: {ALONE}"],
    )


def test_a_task_added_to_another_story_in_the_checkout_of_main_is_written(checkout: Path) -> None:
    outcome = fgraph(TASK_FOR_OTHER, checkout)
    assert (outcome.status, outcome.out) == (0, "added T-0002 to ST-0002\n")
