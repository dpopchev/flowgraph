"""The block of a Feature with the development on: written on main alone, each one commit.

A Story landed while its Feature is blocked starts no next one; the unblock starts it, with its
branch in a worktree of its own, in the commit of the unblock. Run end to end through `run` on a
real git repository in a temporary directory, never a faked git; the identity of its commits
comes from the environment and no git config is read.
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
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
TASK_FOR_OTHER = [
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
ADDED = (ADD_FEATURE, ADD_STORY, ADD_TASK, ADD_OTHER, TASK_FOR_OTHER)
BLOCK = ["block", "F-0001", "--reason", "the budget is not agreed", "--waiting-on", "the sponsor"]
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
LEAF = "S-0001-raise-the-stories-fgraph"
NEXT_LEAF = "S-0002-another-title"
FEATURE_FILE = ".fgraph/items/F-0001.toml"
NEXT_FILE = ".fgraph/items/S-0002.toml"
HELD = "F-0001 is blocked, waiting on the sponsor: unblock it first"
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


def last_commit(cwd: Path) -> tuple[str, list[str]]:
    """The subject of the last commit of the branch cwd is on, and the files it holds."""
    files = git(cwd, "show", "--name-only", "--format=", "HEAD").splitlines()
    return git(cwd, "log", "-1", "--format=%s"), files


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
    """The checkout of main of a repository whose started Feature holds S-0001 ready to land.

    The development is on and the commits of main hold what is added. The Feature is started
    with S-0001, whose one Task is worked and completed in the worktree of its branch; S-0002
    is in Backlog with a Task.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    record = path / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in (*ADDED, ["start", "F-0001"]):
        fgraph(argv, path)
    worktree = tmp_path / "project.worktrees" / LEAF
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    return path


def test_the_block_of_a_feature_on_main_is_one_commit_with_its_file_alone(checkout: Path) -> None:
    fgraph(BLOCK, checkout)
    assert last_commit(checkout) == ("chore: block F-0001 in the record", [FEATURE_FILE])


def test_the_block_of_a_feature_on_the_branch_of_its_story_is_refused(
    checkout: Path, tmp_path: Path
) -> None:
    refused = fgraph(BLOCK, tmp_path / "project.worktrees" / LEAF)
    alone = f"the branch wi/{LEAF} writes S-0001 alone"
    assert (refused.status, refused.err.splitlines()[-1:]) == (
        2,
        [f"fgraph: error: F-0001 is not written here: {alone}"],
    )


class TestAStoryOfABlockedFeatureLandedWhileTheNextIsInBacklog:
    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        fgraph(BLOCK, checkout)
        return fgraph(LAND, checkout)

    def test_land_names_the_next_story_not_started_and_the_block(
        self, landed: Outcome, checkout: Path
    ) -> None:
        merge = git(checkout, "rev-parse", "--short", "HEAD~1")
        assert (landed.status, landed.out) == (
            0,
            f"landed S-0001 at {merge}\nnot started: S-0002 cannot start: {HELD}\n",
        )

    def test_unblock_names_the_next_story_started_then_its_branch_and_its_worktree(
        self, landed: Outcome, checkout: Path, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / NEXT_LEAF
        assert fgraph(["unblock", "F-0001"], checkout).out == (
            f"unblocked F-0001\nstarted S-0002\nbranch wi/{NEXT_LEAF} in {worktree}\n"
        )

    def test_the_unblock_and_the_start_are_one_commit_of_the_record_with_the_files_of_both(
        self, landed: Outcome, checkout: Path
    ) -> None:
        fgraph(["unblock", "F-0001"], checkout)
        assert last_commit(checkout) == (
            "chore: unblock F-0001 and start S-0002 in the record",
            [FEATURE_FILE, NEXT_FILE],
        )
