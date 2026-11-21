"""The criterion of branching at a start: the start is committed and its branch is checked out.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = [
    *("add", "story", TITLE),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
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
    """A git repository on main whose commits hold a Story in Backlog with one Task."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    runs(path, ADD_STORY, ADD_TASK)
    return path


class TestAStoryStartedOnMain:
    @pytest.fixture
    def started(self, checkout: Path) -> Outcome:
        return fgraph(["start", "S-0001"], checkout)

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_start_names_the_branch_and_its_worktree(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / "S-0001-raise-the-stories-fgraph"
        assert started.out == f"started S-0001\nbranch {BRANCH} in {worktree}\n"

    def test_the_start_is_committed_on_main(self, started: Outcome, checkout: Path) -> None:
        assert (
            git(checkout, "log", "-1", "--format=%s", "main") == "chore: start S-0001 in the record"
        )

    def test_the_commit_holds_only_the_file_of_the_story(
        self, started: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "show", "--name-only", "--format=", "main") == (
            ".fgraph/items/S-0001.toml"
        )

    def test_the_branch_is_at_the_commit_of_the_start(
        self, started: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "rev-parse", BRANCH) == git(checkout, "rev-parse", "main")

    def test_the_branch_is_checked_out_in_its_worktree(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / "S-0001-raise-the-stories-fgraph"
        assert git(worktree, "branch", "--show-current") == BRANCH


def test_a_slug_given_names_the_branch(checkout: Path) -> None:
    fgraph(["start", "S-0001", "--slug", "branch-on-start"], checkout)
    assert git(checkout, "branch", "--list", "--format=%(refname:short)", "wi/*") == (
        "wi/S-0001-branch-on-start"
    )


def test_a_change_beside_the_record_stays_out_of_the_commit(checkout: Path) -> None:
    (checkout / "notes.txt").write_text("a change of the development\n", encoding="utf-8")
    git(checkout, "add", "notes.txt")
    fgraph(["start", "S-0001"], checkout)
    assert git(checkout, "status", "--porcelain") == "A  notes.txt"


class TestAStoryStartedOutsideAGitWorkTree:
    @pytest.fixture
    def started(self, tmp_path: Path) -> Outcome:
        path = tmp_path / "project"
        path.mkdir()
        return runs(path, ADD_STORY, ADD_TASK, ["start", "S-0001"])

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_start_names_the_story_alone(self, started: Outcome) -> None:
        assert started.out == "started S-0001\n"

    def test_start_warns_that_no_branch_was_made(self, started: Outcome, tmp_path: Path) -> None:
        assert started.err == (
            f"fgraph: warning: no branch made: {tmp_path / 'project' / '.fgraph'}"
            " is not inside a git work tree\n"
        )


class TestAStartWhoseCommitGitRefuses:
    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        hook = checkout / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho refused by the hook >&2\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        return fgraph(["start", "S-0001"], checkout)

    def test_start_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_start_names_the_git_command_and_its_error(self, refused: Outcome) -> None:
        assert refused.err.splitlines()[-1] == (
            "fgraph: error: git commit --quiet --only --message chore: start S-0001 in the record"
            " -- .fgraph/items/S-0001.toml failed: refused by the hook"
        )

    def test_the_file_of_the_story_is_put_back_as_it_was(
        self, refused: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "status", "--porcelain") == ""


class TestAStartWhoseWorktreeGitRefuses:
    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        git(checkout, "branch", BRANCH)
        return fgraph(["start", "S-0001"], checkout)

    def test_start_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_start_names_the_git_error_and_that_the_start_stays(self, refused: Outcome) -> None:
        assert re.fullmatch(
            rf"fgraph: error: git worktree add .* failed: fatal: a branch named '{BRANCH}'"
            r" already exists -- S-0001 is started at [0-9a-f]{7}, its branch is not",
            refused.err.splitlines()[-1],
        )

    def test_the_start_stays_committed_on_main(self, refused: Outcome, checkout: Path) -> None:
        assert git(checkout, "log", "-1", "--format=%s", "main") == (
            "chore: start S-0001 in the record"
        )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        (
            [["start", "S-0001", "--slug", "Bad Slug"]],
            "'Bad Slug' is no slug: it is lower-case letters and digits joined by hyphens",
        ),
        (
            [["start", "S-0001"], ["start", "T-0001", "--slug", "a-slug"]],
            "--slug names the branch of a work item: T-0001 is a Task",
        ),
    ],
    ids=["slug-of-another-character", "slug-for-a-task"],
)
def test_a_slug_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, checkout: Path
) -> None:
    outcome = runs(checkout, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")
