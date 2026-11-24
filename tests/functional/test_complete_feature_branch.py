"""The completion of a Feature with the development on: its last Story landed on main.

The landing completes the Feature in the commit of the record that completes the Story; on the
branch of the Story nothing completes it. A Story landed while another of its Feature is in
Backlog is in `test_start_next_branch.py`. Run end to end through `run` on a real git repository
in a temporary directory, never a faked git; the identity of its commits comes from the
environment and no git config is read.
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
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists", *CRITERION, "--parent", "F-0001"]
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
ONE_STORY = (ADD_FEATURE, ADD_STORY, ADD_TASK)
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
LEAF = "S-0001-raise-the-stories-fgraph"
BRANCH = f"wi/{LEAF}"
FEATURE_FILE = ".fgraph/items/F-0001.toml"
STORY_FILE = ".fgraph/items/S-0001.toml"
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
        run_check=lambda command, directory: 0,
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def ready_to_land(tmp_path: Path, added: Sequence[Sequence[str]]) -> Path:
    """The checkout of main of a repository whose started Feature holds S-0001 ready to land.

    The development is on and the commits of main hold what is added. The Feature is started
    with S-0001, whose one Task is worked and completed in the worktree of its branch.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in (*added, ["start", "F-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / "project.worktrees" / LEAF
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    return checkout


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


class TestTheLastStoryOfAStartedFeatureLanded:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        return ready_to_land(tmp_path, ONE_STORY)

    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_names_the_story_then_the_feature_completed_at_the_merge_commit(
        self, landed: Outcome, checkout: Path
    ) -> None:
        merge = git(checkout, "rev-parse", "--short", "HEAD~1")
        assert (landed.status, landed.out) == (
            0,
            f"landed S-0001 at {merge}\ncompleted F-0001 at {merge}\n",
        )

    def test_the_complete_is_one_commit_of_the_record_with_the_files_of_both(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "log", "-1", "--format=%s"),
            git(checkout, "show", "--name-only", "--format=", "HEAD").splitlines(),
        ) == ("chore: complete S-0001 and F-0001 in the record", [FEATURE_FILE, STORY_FILE])

    def test_status_lists_the_feature_under_completed_with_the_merge_commit(
        self, landed: Outcome, checkout: Path
    ) -> None:
        merge = git(checkout, "rev-parse", "--short", "HEAD~1")
        assert fgraph(["status"], checkout).out == (
            "Backlog (0)\n"
            "InProgress (0)\n"
            "Completed (1)\n"
            f"  F-0001  1/1 W  {merge}  a feature title\n"
        )

    def test_nothing_is_left_to_commit(self, landed: Outcome, checkout: Path) -> None:
        assert git(checkout, "status", "--porcelain") == ""


class TestTheLastStoryOfAStartedFeatureCompletedOnItsBranch:
    @pytest.fixture
    def worktree(self, tmp_path: Path) -> Path:
        ready_to_land(tmp_path, ONE_STORY)
        return tmp_path / "project.worktrees" / LEAF

    @pytest.fixture
    def refused(self, worktree: Path) -> Outcome:
        return fgraph(["complete", "S-0001", "--commit", "abc1234"], worktree)

    def test_complete_exits_with_two_naming_main_and_the_work_tree_on_it(
        self, refused: Outcome, tmp_path: Path, worktree: Path
    ) -> None:
        on_main = f"main, in {tmp_path / 'project'}"
        assert (refused.status, refused.err.splitlines()[-1]) == (
            2,
            f"fgraph: error: S-0001 completes on {on_main}: {worktree} is on {BRANCH}",
        )

    def test_nothing_is_written(self, refused: Outcome, worktree: Path) -> None:
        assert git(worktree, "status", "--porcelain") == ""
