"""The criterion of S-0141: fgraph watch and fgraph status list the same record in every worktree.

On main the frame is live: both started work items are InProgress with their Task being worked,
and the work item added on main after both starts is in Backlog. The same two commands run in the
worktree of each started work item write that same frame; the eight tests that check it in a
worktree are parametrized over both started work items. Run end to end through `run` on a real
git repository in a temporary directory, never a faked git; the identity of its commits comes
from the environment and no git config is read.
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
DEVELOPMENT_ON = "[development]\nenabled = true\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
FIRST = Path("project.worktrees") / "S-0001-title-1"
SECOND = Path("project.worktrees") / "S-0002-title-2"
WORKTREES = [FIRST, SECOND]
FRAME = (
    "Backlog (1)\n"
    "> S-0003  [1 T]  title 3\n"
    "InProgress (2)\n"
    "  S-0001  0/1 T  title 1\n"
    "    => T-0001  a task title\n"
    "  S-0002  0/1 T  title 2\n"
    "    => T-0002  a task title\n"
    "Completed (0)\n"
)


def story(number: int) -> list[str]:
    """The command that adds the Story of that title."""
    return ["add", "story", f"title {number}", *CRITERION]


def task(parent: str) -> list[str]:
    """The command that adds a Task with a check to that work item."""
    return [
        "add",
        "task",
        "a task title",
        "--parent",
        parent,
        "--output",
        "an output",
        "--check",
        "make test",
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
    """The checkout of main, with S-0001 and S-0002 started in their worktrees and S-0003 added."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text(DEVELOPMENT_ON, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in (
        story(1),
        story(2),
        task("S-0001"),
        task("S-0002"),
        ["start", "S-0001"],
        ["start", "S-0002"],
    ):
        fgraph(argv, path)
    fgraph(["start", "T-0001"], tmp_path / FIRST)
    fgraph(["start", "T-0002"], tmp_path / SECOND)
    fgraph(story(3), path)
    fgraph(task("S-0003"), path)
    return path


@pytest.fixture
def limited(checkout: Path) -> Path:
    """The checkout of main with development.parallel set to 2."""
    fgraph(["config", "set", "development.parallel", "2"], checkout)
    return checkout


class TestGuardsThatPassToday:
    def test_watch_on_main_draws_the_frame(self, checkout: Path) -> None:
        assert fgraph(["watch", "--count", "1"], checkout).out == FRAME

    def test_status_on_main_prints_the_frame(self, checkout: Path) -> None:
        assert fgraph(["status"], checkout).out == FRAME

    def test_under_parallel_two_main_lists_the_one_added_after_unmarked(
        self, limited: Path
    ) -> None:
        assert "  S-0003  [1 T]  title 3" in fgraph(["status"], limited).out.splitlines()

    def test_with_no_work_tree_on_main_a_worktree_lists_its_own_record(
        self, checkout: Path, tmp_path: Path
    ) -> None:
        git(checkout, "switch", "--quiet", "--create", "elsewhere")
        assert "> S-0002  [1 T]  title 2" in fgraph(["status"], tmp_path / FIRST).out.splitlines()

    def test_show_in_a_worktree_reads_the_record_of_that_worktree(
        self, checkout: Path, tmp_path: Path
    ) -> None:
        shown = fgraph(["show", "S-0002"], tmp_path / FIRST).out.splitlines()
        assert shown[1].split() == ["bucket", "Backlog"]


@pytest.mark.parametrize("worktree", WORKTREES, ids=["of-S-0001", "of-S-0002"])
class TestWorktreesListTheRecordOfMain:
    def test_watch_in_a_worktree_draws_the_frame_main_draws(
        self, checkout: Path, tmp_path: Path, worktree: Path
    ) -> None:
        assert fgraph(["watch", "--count", "1"], tmp_path / worktree).out == FRAME

    def test_status_in_a_worktree_prints_the_frame_main_prints(
        self, checkout: Path, tmp_path: Path, worktree: Path
    ) -> None:
        assert fgraph(["status"], tmp_path / worktree).out == FRAME

    def test_status_as_json_in_a_worktree_prints_the_bytes_main_prints(
        self, checkout: Path, tmp_path: Path, worktree: Path
    ) -> None:
        assert (
            fgraph(["status", "--format", "json"], tmp_path / worktree).out
            == fgraph(["status", "--format", "json"], checkout).out
        )

    def test_under_parallel_two_a_worktree_lists_the_one_added_after_unmarked(
        self, limited: Path, tmp_path: Path, worktree: Path
    ) -> None:
        assert (
            "  S-0003  [1 T]  title 3" in fgraph(["status"], tmp_path / worktree).out.splitlines()
        )
