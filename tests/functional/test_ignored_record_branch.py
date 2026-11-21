"""The criterion of a branch on an ignored record: `fgraph start` makes the branch of the Story.

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

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
MESSAGE = "feat: land the first Story"
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
    """A git repository on main whose `.gitignore` names the record, holding a Story with a Task."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".gitignore").write_text(".fgraph/\n", encoding="utf-8")
    git(path, "add", ".gitignore")
    git(path, "commit", "--quiet", "--message", "first")
    fgraph(ADD_STORY, path)
    fgraph(ADD_TASK, path)
    return path


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Where the worktree of the branch of the Story is checked out."""
    return tmp_path / WORKTREE


class TestAStoryStartedOnMainOnARecordGitIgnores:
    @pytest.fixture
    def started(self, checkout: Path) -> Outcome:
        return fgraph(["start", "S-0001"], checkout)

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_start_names_the_branch_and_its_worktree(
        self, started: Outcome, worktree: Path
    ) -> None:
        assert started.out == f"started S-0001\nbranch {BRANCH} in {worktree}\n"

    def test_start_warns_of_nothing(self, started: Outcome) -> None:
        assert started.err == ""

    def test_the_branch_is_checked_out_in_its_worktree(
        self, started: Outcome, worktree: Path
    ) -> None:
        assert git(worktree, "branch", "--show-current") == BRANCH

    def test_the_branch_is_at_the_head_of_main(
        self, started: Outcome, checkout: Path, worktree: Path
    ) -> None:
        assert git(worktree, "rev-parse", "HEAD") == git(checkout, "rev-parse", "HEAD")

    def test_no_commit_is_made(self, started: Outcome, checkout: Path) -> None:
        assert git(checkout, "rev-list", "--count", "HEAD") == "1"

    def test_a_task_of_the_story_is_started_in_the_checkout_of_main(
        self, started: Outcome, checkout: Path
    ) -> None:
        outcome = fgraph(["start", "T-0001"], checkout)
        assert (outcome.status, outcome.out) == (0, "started T-0001 of S-0001\n")


class TestAStoryLandedOnARecordGitIgnores:
    @pytest.fixture
    def landed(self, checkout: Path, worktree: Path) -> Outcome:
        fgraph(["start", "S-0001"], checkout)
        fgraph(["start", "T-0001"], checkout)
        (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
        git(worktree, "add", "work.txt")
        git(worktree, "commit", "--quiet", "--message", "feat: do the work")
        fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], checkout)
        return fgraph(["land", "S-0001", "--message", MESSAGE], checkout)

    def test_land_exits_with_zero(self, landed: Outcome) -> None:
        assert landed.status == 0

    def test_land_names_the_merge_commit(self, landed: Outcome, checkout: Path) -> None:
        assert landed.out == f"landed S-0001 at {git(checkout, 'rev-parse', '--short', 'HEAD')}\n"

    def test_the_merge_commit_is_the_last_of_main_under_the_message(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "log", "-1", "--format=%s") == MESSAGE

    def test_the_record_is_not_committed(self, landed: Outcome, checkout: Path) -> None:
        assert git(checkout, "rev-list", "--count", "HEAD") == "3"

    def test_status_lists_the_story_under_completed_with_the_merge_commit(
        self, landed: Outcome, checkout: Path
    ) -> None:
        sha = git(checkout, "rev-parse", "--short", "HEAD")
        assert fgraph(["status"], checkout).out.splitlines()[-2:] == [
            "Completed (1)",
            f"  S-0001  {sha}  Raise the Stories fgraph lists from 0 to 1",
        ]

    def test_the_branch_is_removed(self, landed: Outcome, checkout: Path) -> None:
        assert git(checkout, "branch", "--list", "wi/*") == ""

    def test_the_worktree_is_removed(self, landed: Outcome, worktree: Path) -> None:
        assert not worktree.exists()


def test_a_story_started_off_main_on_a_record_git_ignores_names_main(checkout: Path) -> None:
    git(checkout, "switch", "--quiet", "--create", "a-feature")
    outcome = fgraph(["start", "S-0001"], checkout)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        [f"fgraph: error: S-0001 starts on main: {checkout} is on a-feature"],
    )
