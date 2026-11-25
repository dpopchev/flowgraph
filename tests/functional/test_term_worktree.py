"""The criterion of terms across worktrees: a term is written on main alone, read from a worktree.

The worktree of a started work item reads the terms of the record of main, as it reads the Task
ids of every worktree; a term added or related on its branch is refused naming the work item the
branch owns.
Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
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
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
BEFORE = ["add", "term", "gate", "--means", "a check every deliverable passes"]
AFTER = ["add", "term", "lane", "--means", "one work item in its own worktree"]
RELATE = ["relate", "gate", "part-of", "lane"]
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
    """The checkout of main and the worktree of started S-0001, a term added before and after.

    The term added before the start is in the branch of the worktree too; the one added after it
    is on main alone.
    """
    path = tmp_path / "project"
    (path / ".fgraph").mkdir(parents=True)
    git(path, "init", "--quiet", "--initial-branch", "main")
    config = path / ".fgraph" / "config.toml"
    config.write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in (ADD_STORY, ADD_TASK, BEFORE, ["start", "S-0001"], AFTER):
        fgraph(argv, path)
    return path


class TestTermsReadInTheWorktreeOfAStartedWorkItem:
    @pytest.fixture
    def listed(self, checkout: Path, tmp_path: Path) -> Outcome:
        return fgraph(["terms"], tmp_path / WORKTREE)

    def test_terms_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_terms_lists_those_of_main_as_main_holds_them(self, listed: Outcome) -> None:
        assert listed.out == (
            "gate  a check every deliverable passes\nlane  one work item in its own worktree\n"
        )

    def test_show_of_a_term_added_on_main_after_the_start_prints_its_meaning(
        self, checkout: Path, tmp_path: Path
    ) -> None:
        shown = fgraph(["show", "lane"], tmp_path / WORKTREE)
        assert "one work item in its own worktree" in shown.out


class TestATermAddedOnTheBranchOfAWorkItem:
    @pytest.fixture
    def refused(self, checkout: Path, tmp_path: Path) -> Outcome:
        return fgraph(["add", "term", "other", "--means", "a meaning"], tmp_path / WORKTREE)

    def test_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_names_the_work_item_the_branch_owns(self, refused: Outcome) -> None:
        assert refused.err.endswith(
            f"fgraph: error: other is not added here: the branch {BRANCH} writes S-0001 alone\n"
        )

    def test_writes_no_file(self, refused: Outcome, tmp_path: Path) -> None:
        assert not (tmp_path / WORKTREE / ".fgraph" / "terms" / "other.toml").exists()


class TestATermRelatedOnTheBranchOfAWorkItem:
    @pytest.fixture
    def refused(self, checkout: Path, tmp_path: Path) -> Outcome:
        return fgraph(RELATE, tmp_path / WORKTREE)

    def test_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_names_the_work_item_the_branch_owns_and_says_the_term_is_not_related(
        self, refused: Outcome
    ) -> None:
        assert refused.err.endswith(
            f"fgraph: error: gate is not related here: the branch {BRANCH} writes S-0001 alone\n"
        )

    def test_writes_no_relation(self, refused: Outcome, tmp_path: Path) -> None:
        gate = tmp_path / "project" / ".fgraph" / "terms" / "gate.toml"
        assert "lane" not in gate.read_text(encoding="utf-8")
