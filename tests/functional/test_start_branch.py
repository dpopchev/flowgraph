"""The criterion of branching at a start: the start is committed and its branch is checked out.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="ST-0009: fgraph start makes no branch yet"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = [
    *("add", "story", TITLE),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
BRANCH = "wi/ST-0001-raise-the-stories-fgraph"
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
    # Imported here, unchecked, until T-0043 adds it to flowgraph.cli; then at the top.
    from flowgraph.cli import GIT  # pyright: ignore[reportAttributeAccessIssue]

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
        git=GIT,  # pyright: ignore[reportCallIssue]
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
    """A git repository on main whose first commit holds a Story in Backlog with one Task."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    runs(path, ADD_STORY, ADD_TASK)
    git(path, "add", ".fgraph")
    git(path, "commit", "--quiet", "--message", "chore: write ST-0001 in the record")
    return path


class TestAStoryStartedOnMain:
    @pytest.fixture
    def started(self, checkout: Path) -> Outcome:
        return fgraph(["start", "ST-0001"], checkout)

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_start_names_the_branch_and_its_worktree(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / "ST-0001-raise-the-stories-fgraph"
        assert started.out == f"started ST-0001\nbranch {BRANCH} in {worktree}\n"

    def test_the_start_is_committed_on_main(self, started: Outcome, checkout: Path) -> None:
        assert (
            git(checkout, "log", "-1", "--format=%s", "main")
            == "chore: start ST-0001 in the record"
        )

    def test_the_commit_holds_only_the_file_of_the_story(
        self, started: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "show", "--name-only", "--format=", "main") == (
            ".fgraph/items/ST-0001.toml"
        )

    def test_the_branch_is_at_the_commit_of_the_start(
        self, started: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "rev-parse", BRANCH) == git(checkout, "rev-parse", "main")

    def test_the_branch_is_checked_out_in_its_worktree(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / "ST-0001-raise-the-stories-fgraph"
        assert git(worktree, "branch", "--show-current") == BRANCH


def test_a_slug_given_names_the_branch(checkout: Path) -> None:
    fgraph(["start", "ST-0001", "--slug", "branch-on-start"], checkout)
    assert git(checkout, "branch", "--list", "--format=%(refname:short)", "wi/*") == (
        "wi/ST-0001-branch-on-start"
    )


def test_a_change_beside_the_record_stays_out_of_the_commit(checkout: Path) -> None:
    (checkout / "notes.txt").write_text("a change of the development\n", encoding="utf-8")
    git(checkout, "add", "notes.txt")
    fgraph(["start", "ST-0001"], checkout)
    assert git(checkout, "status", "--porcelain") == "A  notes.txt"


class TestAStoryStartedOutsideAGitWorkTree:
    @pytest.fixture
    def started(self, tmp_path: Path) -> Outcome:
        path = tmp_path / "project"
        path.mkdir()
        return runs(path, ADD_STORY, ADD_TASK, ["start", "ST-0001"])

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_start_names_the_story_alone(self, started: Outcome) -> None:
        assert started.out == "started ST-0001\n"

    def test_start_warns_that_no_branch_was_made(self, started: Outcome, tmp_path: Path) -> None:
        assert started.err == (
            f"fgraph: warning: no branch made: {tmp_path / 'project' / '.fgraph'}"
            " is not inside a git work tree\n"
        )
