"""The criterion of S-0126: a started work item is handed to an agent where its Tasks are written.

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
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = [
    *("add", "story", TITLE),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
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
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_FIRST = [*ADD_STORY[:3], *CRITERION, "--parent", "F-0001"]
ADD_SECOND = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
TASK_OF_SECOND = [*ADD_TASK[:4], "S-0002", *ADD_TASK[5:]]
ADD_FEATURE_STORIES = (ADD_FEATURE, ADD_FIRST, ADD_TASK, ADD_SECOND, TASK_OF_SECOND)
ADD_THIRD = ["add", "story", "a third title", *CRITERION]
TASK_OF_THIRD = [*ADD_TASK[:4], "S-0003", *ADD_TASK[5:]]
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
LAND_THIRD = ["land", "S-0003", "--message", "feat: land the third Story"]
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


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def enable_development(project: Path) -> None:
    """Write `[development] enabled = true` as the config.toml of the record of the project."""
    record = project / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")


def finish_task(worktree: Path, task: str) -> None:
    """Start the Task in its worktree, commit a file and complete the Task at that commit."""
    fgraph(["start", task], worktree)
    (worktree / f"{task}.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", f"{task}.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", task, "--commit", git(worktree, "rev-parse", "HEAD")], worktree)


def listed(checkout: Path, item: str) -> str:
    """The line status prints for the item, from its id on."""
    out = fgraph(["status"], checkout).out
    return next(line.strip() for line in out.splitlines() if line.strip().startswith(item))


def shown(checkout: Path, *words: str) -> list[str]:
    """The lines of show S-0003 that start with one of the words after two spaces."""
    lines = fgraph(["show", "S-0003"], checkout).out.splitlines()
    return [line for line in lines if line.startswith(tuple(f"  {word}" for word in words))]


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
def repository(tmp_path: Path) -> Path:
    """A git repository on main whose first commit holds the config.toml of the record.

    The config turns the development on.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    enable_development(path)
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    return path


@pytest.fixture
def worktrees(tmp_path: Path) -> tuple[Path, Path]:
    """The worktrees of S-0002 and of S-0003, where their branches are checked out."""
    base = tmp_path / "project.worktrees"
    return base / "S-0002-another-title", base / "S-0003-a-third-title"


@pytest.fixture
def started(repository: Path, tmp_path: Path) -> Path:
    """S-0001 started with no agent, S-0003 with sonnet-a1, S-0002 started by the landing of S-0001.

    S-0002 holds no agent: a landing starts it.
    """
    runs(repository, *ADD_FEATURE_STORIES, ADD_THIRD, TASK_OF_THIRD)
    runs(repository, ["start", "F-0001"], ["start", "S-0003", "--agent", "sonnet-a1"])
    finish_task(tmp_path / "project.worktrees" / "S-0001-raise-the-stories-fgraph", "T-0001")
    fgraph(LAND, repository)
    return repository


@pytest.fixture
def handed(started: Path, worktrees: tuple[Path, Path]) -> tuple[Outcome, Outcome]:
    """The hand of S-0002 from main with --dir, and the hand of S-0003 in its worktree."""
    second, third = worktrees
    record = str(second / ".fgraph")
    from_main = fgraph(["--dir", record, "hand", "S-0002", "--agent", "haiku-b1"], started)
    in_worktree = fgraph(["hand", "S-0003", "--agent", "opus-b2"], third)
    return from_main, in_worktree


class TestTwoStartedWorkItemsHanded:
    def test_the_hand_of_the_second_story_from_main_exits_with_zero(
        self, handed: tuple[Outcome, Outcome]
    ) -> None:
        assert handed[0].status == 0

    def test_the_hand_of_the_third_story_in_its_worktree_exits_with_zero(
        self, handed: tuple[Outcome, Outcome]
    ) -> None:
        assert handed[1].status == 0

    def test_the_hand_of_the_third_story_says_what_it_did(
        self, handed: tuple[Outcome, Outcome]
    ) -> None:
        assert handed[1].out == "handed S-0003 to opus-b2\n"

    def test_status_lists_the_new_agent_beside_the_second_story(
        self, handed: tuple[Outcome, Outcome], started: Path
    ) -> None:
        assert listed(started, "S-0002") == "S-0002  0/1 T  [haiku-b1]  another title"

    def test_status_lists_the_new_agent_beside_the_third_story(
        self, handed: tuple[Outcome, Outcome], started: Path
    ) -> None:
        assert listed(started, "S-0003") == "S-0003  0/1 T  [opus-b2]  a third title"

    def test_show_lists_the_agent_the_third_story_holds_now_alone(
        self, handed: tuple[Outcome, Outcome], started: Path
    ) -> None:
        assert shown(started, "agent") == ["  agent        opus-b2"]

    def test_the_branch_of_the_third_story_holds_the_commit_of_the_hand(
        self, handed: tuple[Outcome, Outcome], worktrees: tuple[Path, Path]
    ) -> None:
        assert git(worktrees[1], "log", "-1", "--format=%s") == (
            "chore: hand S-0003 to opus-b2 in the record"
        )

    def test_the_hand_on_main_is_refused_naming_the_worktree(
        self, handed: tuple[Outcome, Outcome], started: Path, worktrees: tuple[Path, Path]
    ) -> None:
        refused = fgraph(["hand", "S-0003", "--agent", "opus-b2"], started)
        started_in = "fgraph: error: S-0003 is started: its Tasks are written in its worktree"
        expected = f"{started_in}, {worktrees[1]}"
        assert (refused.status, refused.err.splitlines()[-1]) == (2, expected)


class TestAThirdStoryHandedThenLanded:
    @pytest.fixture
    def landed(
        self, handed: tuple[Outcome, Outcome], started: Path, worktrees: tuple[Path, Path]
    ) -> Outcome:
        finish_task(worktrees[1], "T-0003")
        return fgraph(LAND_THIRD, started)

    def test_it_is_completed_and_keeps_the_agent_it_was_handed_to(
        self, landed: Outcome, started: Path
    ) -> None:
        assert shown(started, "bucket", "agent") == [
            "  bucket       Completed",
            "  agent        opus-b2",
        ]
