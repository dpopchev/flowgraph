"""The start of a Feature with the development on: one commit, and the branch of its first Story.

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
ADD_ALONE = ["add", "story", "a title that stands alone", *CRITERION]
TASK_FOR_ALONE = [
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
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists", *CRITERION, "--parent", "F-0001"]
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
ADDED = (ADD_ALONE, TASK_FOR_ALONE, ADD_FEATURE, ADD_STORY, ADD_TASK)
LEAF = "S-0002-raise-the-stories-fgraph"
BRANCH = f"wi/{LEAF}"
DEVELOPMENT_ON = "[development]\nenabled = true\n"
ONE_AT_ONCE = "[development]\nenabled = true\nparallel = 1\n"
REFUSAL = "F-0001 cannot start: development.parallel = 1, started already: S-0001"
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


def checkout_under(path: Path, config: str) -> Path:
    """A git repository on main at the path under that config.toml, its commits holding ADDED.

    S-0001 stands alone and F-0001 holds S-0002, each Story in Backlog with one Task.
    """
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    record = path / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text(config, encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in ADDED:
        fgraph(argv, path)
    return path


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


class TestAFeatureStartedOnMain:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        return checkout_under(tmp_path / "project", DEVELOPMENT_ON)

    @pytest.fixture
    def started(self, checkout: Path) -> Outcome:
        return fgraph(["start", "F-0001"], checkout)

    def test_start_names_the_branch_of_its_first_story_and_its_worktree(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / LEAF
        assert (started.status, started.out) == (
            0,
            f"started F-0001 with S-0002\nbranch {BRANCH} in {worktree}\n",
        )

    def test_the_start_is_one_commit_on_main(self, started: Outcome, checkout: Path) -> None:
        assert git(checkout, "log", "-2", "--format=%s", "main").splitlines() == [
            "chore: start F-0001 in the record",
            "chore: add T-0002 of S-0002 in the record",
        ]

    def test_the_commit_holds_the_file_of_the_feature_and_that_of_its_first_story(
        self, started: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "show", "--name-only", "--format=", "main").splitlines() == [
            ".fgraph/items/F-0001.toml",
            ".fgraph/items/S-0002.toml",
        ]

    def test_the_branch_of_its_first_story_is_at_the_commit_of_the_start(
        self, started: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "rev-parse", BRANCH) == git(checkout, "rev-parse", "main")

    def test_the_branch_is_checked_out_in_its_worktree(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / LEAF
        assert git(worktree, "branch", "--show-current") == BRANCH

    def test_a_feature_is_not_started_in_the_worktree_of_its_story(
        self, started: Outcome, checkout: Path, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / LEAF
        refused = fgraph(["start", "F-0001"], worktree)
        assert (refused.status, refused.err.splitlines()[-1]) == (
            2,
            f"fgraph: error: F-0001 starts on main, in {checkout}: {worktree} is on {BRANCH}",
        )


def test_a_slug_given_names_the_branch_of_the_first_story(tmp_path: Path) -> None:
    checkout = checkout_under(tmp_path / "project", DEVELOPMENT_ON)
    fgraph(["start", "F-0001", "--slug", "a-slug"], checkout)
    assert git(checkout, "branch", "--list", "--format=%(refname:short)", "wi/*") == (
        "wi/S-0002-a-slug"
    )


class TestAFeatureStartedBesideAStartedStoryUnderParallelOne:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = checkout_under(tmp_path / "project", ONE_AT_ONCE)
        fgraph(["start", "S-0001"], path)
        return path

    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        return fgraph(["start", "F-0001"], checkout)

    def test_start_exits_with_two_naming_the_started_story(self, refused: Outcome) -> None:
        assert (refused.status, refused.err.splitlines()[-1:]) == (2, [f"fgraph: error: {REFUSAL}"])

    def test_nothing_is_written_after_the_start_of_the_story_standing_alone(
        self, refused: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "status", "--porcelain"),
            git(checkout, "log", "-1", "--format=%s", "main"),
        ) == ("", "chore: start S-0001 in the record")

    def test_no_branch_is_made_for_the_first_story_of_the_feature(
        self, refused: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "branch", "--list", "--format=%(refname:short)", "wi/*") == (
            "wi/S-0001-a-title-that-stands"
        )
