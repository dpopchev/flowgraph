"""The criterion of a landing by squash: main gains one commit holding the work of the branch.

The record turns the development on with `[development] merge = "squash"`. Run end to end
through `run` on a real git repository in a temporary directory, never a faked git; the identity
of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0043: development.merge is no key yet"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
MESSAGE = "feat: land the first Story"
LAND = ["land", "S-0001", "--message", MESSAGE]
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
SQUASH = '[development]\nenabled = true\nmerge = "squash"\n'
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


@dataclass(frozen=True)
class Landed:
    """A landing run: what it left, the commit main was on before it and the tree of the branch."""

    outcome: Outcome
    before: str
    tree: str


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


def merge_by_squash(checkout: Path) -> None:
    """Commit the config.toml of the record of the checkout: the development on, merge = squash."""
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text(SQUASH, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: land a work item by squash")


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
def ready(tmp_path: Path) -> Path:
    """The checkout of main under merge = squash, holding a started Story ready to land.

    Its one Task is started in the worktree of its branch, the work of the Task is committed
    there and the Task is completed at that commit: the branch is three commits ahead of main.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    merge_by_squash(checkout)
    for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    return checkout


class TestAStoryLandedBySquash:
    @pytest.fixture
    def landed(self, ready: Path) -> Landed:
        before = git(ready, "rev-parse", "HEAD")
        tree = git(ready, "rev-parse", f"{BRANCH}^{{tree}}")
        return Landed(fgraph(LAND, ready), before, tree)

    def test_land_exits_with_zero(self, landed: Landed) -> None:
        assert landed.outcome.status == 0

    def test_main_gains_one_commit_worded_by_the_developer_before_that_of_the_record(
        self, landed: Landed, ready: Path
    ) -> None:
        assert git(ready, "log", "--format=%s", f"{landed.before}..HEAD").splitlines() == [
            "chore: complete S-0001 in the record",
            MESSAGE,
        ]

    def test_the_one_parent_of_that_commit_is_the_commit_main_was_on(
        self, landed: Landed, ready: Path
    ) -> None:
        assert git(ready, "rev-list", "--parents", "-n", "1", "HEAD~1").split()[1:] == [
            landed.before
        ]

    def test_that_commit_holds_the_work_of_the_branch(self, landed: Landed, ready: Path) -> None:
        assert git(ready, "rev-parse", "HEAD~1^{tree}") == landed.tree

    def test_land_names_the_story_and_that_commit(self, landed: Landed, ready: Path) -> None:
        commit = git(ready, "rev-parse", "--short", "HEAD~1")
        assert landed.outcome.out == f"landed S-0001 at {commit}\n"

    def test_status_lists_it_under_completed_with_that_commit(
        self, landed: Landed, ready: Path
    ) -> None:
        commit = git(ready, "rev-parse", "--short", "HEAD~1")
        assert fgraph(["status"], ready).out == (
            f"Backlog (0)\nInProgress (0)\nCompleted (1)\n  S-0001  {commit}  {TITLE}\n"
        )

    def test_the_worktree_of_the_branch_is_removed(self, landed: Landed, tmp_path: Path) -> None:
        assert not (tmp_path / WORKTREE).exists()

    def test_the_branch_is_removed(self, landed: Landed, ready: Path) -> None:
        assert git(ready, "branch", "--list", "wi/*") == ""

    def test_nothing_is_left_to_commit(self, landed: Landed, ready: Path) -> None:
        assert git(ready, "status", "--porcelain") == ""
