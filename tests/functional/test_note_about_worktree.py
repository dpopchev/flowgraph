"""A line noted on the branch of a started work item is checked against the terms of main.

A term is written on main alone, so a term added on main after the branch was cut is accepted
there. Run end to end through `run` on a real git repository in a temporary directory, never a
faked git; the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
NOTE_LANE = ["note", "S-0001", "--finding", "a lane is one item", "--about", "lane"]
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


def fgraph(argv: list[str], cwd: Path) -> Outcome:
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
    """The checkout of main and the worktree of started S-0001; the term lane is added after.

    The term lane is on main alone: the branch of the worktree was cut before it.
    """
    path = tmp_path / "project"
    (path / ".fgraph").mkdir(parents=True)
    git(path, "init", "--quiet", "--initial-branch", "main")
    config = path / ".fgraph" / "config.toml"
    config.write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    after = ["add", "term", "lane", "--means", "one work item in its own worktree"]
    for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"], after):
        fgraph(argv, path)
    return path


class TestALineNotedOnTheBranchAboutATermAddedOnMainAfterIt:
    @pytest.fixture
    def noted(self, checkout: Path, tmp_path: Path) -> Outcome:
        return fgraph(NOTE_LANE, tmp_path / WORKTREE)

    def test_note_exits_with_zero(self, noted: Outcome) -> None:
        assert noted.status == 0

    def test_show_of_the_work_item_there_lists_the_line_with_the_term(
        self, noted: Outcome, tmp_path: Path
    ) -> None:
        shown = fgraph(["show", "S-0001"], tmp_path / WORKTREE)
        assert "  finding  2026-01-01  a lane is one item  (about lane)\n" in shown.out


def test_a_term_that_main_holds_none_of_is_refused_on_the_branch(
    checkout: Path, tmp_path: Path
) -> None:
    refused = fgraph([*NOTE_LANE[:-1], "nope"], tmp_path / WORKTREE)
    assert (refused.status, refused.err.splitlines()[-1]) == (
        2,
        "fgraph: error: no term 'nope' in the record: add it with fgraph add term",
    )
