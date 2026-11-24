"""A supersede noted in the worktree of a started work item writes the file of that item alone.

The line superseded is on main and only read; fgraph show on main lists it as superseded, read
across the worktrees. Run end to end through `run` on a real git repository in a temporary
directory, never a faked git; the identity of its commits comes from the environment and no git
config is read.
"""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

XFAIL = pytest.mark.xfail(strict=True, reason="S-0103: fgraph note takes no --supersedes")

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
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
WORKTREE = Path("project.worktrees") / "S-0002-raise-the-stories-fgraph"
SUPERSEDE = ["note", "S-0002", "--decision", "keep one file per item", "--supersedes", "S-0001#1"]
SUPERSEDED = "  decision  2026-01-01  keep one store  (superseded by S-0002#1)\n"
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
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def held(checkout: Path) -> str:
    """The text of the file of S-0001 on main."""
    return (checkout / ".fgraph" / "items" / "S-0001.toml").read_text(encoding="utf-8")


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
    """The checkout of main, S-0001 with a decision noted on main, and S-0002 started."""
    path = tmp_path / "project"
    (path / ".fgraph").mkdir(parents=True)
    git(path, "init", "--quiet", "--initial-branch", "main")
    config = path / ".fgraph" / "config.toml"
    config.write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in (
        ["add", "story", "a title that stands", *CRITERION],
        ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION],
        ADD_TASK,
        ["note", "S-0001", "--decision", "keep one store"],
        ["start", "S-0002"],
    ):
        fgraph(argv, path)
    return path


class TestASupersedeNotedInTheWorktreeOfAStartedWorkItem:
    @pytest.fixture
    def before(self, checkout: Path) -> str:
        return held(checkout)

    @pytest.fixture
    def noted(self, before: str, tmp_path: Path) -> Outcome:
        return fgraph(SUPERSEDE, tmp_path / WORKTREE)

    @XFAIL
    def test_note_exits_with_zero_and_says_noted(self, noted: Outcome) -> None:
        assert (noted.status, noted.out) == (0, "noted S-0002\n")

    @XFAIL
    def test_the_worktree_commits_the_file_of_the_work_item_alone(
        self, noted: Outcome, tmp_path: Path
    ) -> None:
        worktree = tmp_path / WORKTREE
        assert (
            git(worktree, "log", "-1", "--format=%s"),
            git(worktree, "show", "--name-only", "--format=", "HEAD"),
        ) == ("chore: note S-0002 in the record", ".fgraph/items/S-0002.toml")

    @XFAIL
    def test_main_is_left_clean_and_the_file_of_the_first_as_written(
        self, noted: Outcome, before: str, checkout: Path
    ) -> None:
        assert (noted.status, git(checkout, "status", "--porcelain"), held(checkout) == before) == (
            0,
            "",
            True,
        )

    @XFAIL
    def test_show_on_main_lists_the_first_as_superseded(
        self, noted: Outcome, checkout: Path
    ) -> None:
        assert SUPERSEDED in fgraph(["show", "S-0001"], checkout).out

    @XFAIL
    def test_show_in_the_worktree_lists_the_first_as_superseded(
        self, noted: Outcome, tmp_path: Path
    ) -> None:
        assert SUPERSEDED in fgraph(["show", "S-0001"], tmp_path / WORKTREE).out
