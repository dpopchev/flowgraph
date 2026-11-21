"""The criterion of landing: `fgraph land` leaves the Story Completed at the merge of its branch.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
LAND = ["land", "ST-0001", "--message", "feat: land the first Story"]
BRANCH = "wi/ST-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "ST-0001-raise-the-stories-fgraph"
STORY_FILE = ".fgraph/items/ST-0001.toml"
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
def started(tmp_path: Path) -> Path:
    """The checkout of main of a repository holding a started Story with its worktree branch.

    Its one Task is started in the worktree, and the work of the Task is committed there.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    for argv in (ADD_STORY, ADD_TASK, ["start", "ST-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    return checkout


@pytest.fixture
def ready(started: Path, tmp_path: Path) -> Path:
    """The checkout of main, every Task of the started Story completed on its worktree branch."""
    worktree = tmp_path / WORKTREE
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    return started


class TestAStoryLandedInTheCheckoutOfMain:
    @pytest.fixture
    def landed(self, ready: Path) -> Outcome:
        return fgraph(LAND, ready)

    def test_land_exits_with_zero(self, landed: Outcome) -> None:
        assert landed.status == 0

    def test_land_names_the_story_and_the_merge_commit(self, landed: Outcome, ready: Path) -> None:
        assert landed.out == f"landed ST-0001 at {git(ready, 'rev-parse', '--short', 'HEAD~1')}\n"

    def test_status_lists_it_under_completed_with_the_merge_commit(
        self, landed: Outcome, ready: Path
    ) -> None:
        merge = git(ready, "rev-parse", "--short", "HEAD~1")
        assert fgraph(["status"], ready).out == (
            f"Backlog (0)\nInProgress (0)\nCompleted (1)\n  ST-0001  {TITLE}  {merge}\n"
        )

    def test_the_merge_commit_is_worded_by_the_developer(
        self, landed: Outcome, ready: Path
    ) -> None:
        assert git(ready, "log", "-1", "--format=%s", "HEAD~1") == "feat: land the first Story"

    def test_the_merge_commit_joins_main_and_the_branch(self, landed: Outcome, ready: Path) -> None:
        assert len(git(ready, "rev-list", "--parents", "-n", "1", "HEAD~1").split()) == 3

    def test_the_work_of_the_branch_is_on_main(self, landed: Outcome, ready: Path) -> None:
        assert (ready / "work.txt").read_text(encoding="utf-8") == "the work of the Task\n"

    def test_the_complete_is_committed_by_fgraph_with_the_file_of_the_story(
        self, landed: Outcome, ready: Path
    ) -> None:
        assert (
            git(ready, "log", "-1", "--format=%s"),
            git(ready, "show", "--name-only", "--format=", "HEAD"),
        ) == ("chore: complete ST-0001 in the record", STORY_FILE)

    def test_the_worktree_of_the_branch_is_removed(self, landed: Outcome, tmp_path: Path) -> None:
        assert not (tmp_path / WORKTREE).exists()

    def test_the_branch_is_removed(self, landed: Outcome, ready: Path) -> None:
        assert git(ready, "branch", "--list", "wi/*") == ""

    def test_nothing_is_left_to_commit(self, landed: Outcome, ready: Path) -> None:
        assert git(ready, "status", "--porcelain") == ""


class TestALandWithATaskNotCompleted:
    @pytest.fixture
    def refused(self, started: Path) -> tuple[Outcome, str]:
        before = git(started, "rev-parse", "HEAD")
        return fgraph(LAND, started), before

    def test_land_exits_with_two(self, refused: tuple[Outcome, str]) -> None:
        assert refused[0].status == 2

    def test_land_names_the_task_to_complete_first(self, refused: tuple[Outcome, str]) -> None:
        assert refused[0].err.splitlines()[-1:] == [
            "fgraph: error: ST-0001 has Tasks to complete first: T-0001"
        ]

    def test_nothing_is_merged(self, refused: tuple[Outcome, str], started: Path) -> None:
        assert (git(started, "rev-parse", "HEAD"), git(started, "status", "--porcelain")) == (
            refused[1],
            "",
        )

    def test_the_branch_stays(self, refused: tuple[Outcome, str], started: Path) -> None:
        assert git(started, "branch", "--list", "--format=%(refname:short)", "wi/*") == BRANCH


def test_a_land_in_a_checkout_that_is_not_on_main_exits_with_two_and_names_it(
    ready: Path, tmp_path: Path
) -> None:
    outcome = fgraph(LAND, tmp_path / WORKTREE)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        [f"fgraph: error: ST-0001 lands on main: {tmp_path / WORKTREE} is on {BRANCH}"],
    )


def test_a_land_of_a_story_without_a_branch_exits_with_two_and_names_it(ready: Path) -> None:
    fgraph(ADD_OTHER, ready)
    outcome = fgraph(["land", "ST-0002", "--message", "feat: land another"], ready)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: ST-0002 has no branch wi/ST-0002-* to land"],
    )


def test_a_land_outside_a_git_work_tree_exits_with_two_and_names_the_record(
    tmp_path: Path,
) -> None:
    fgraph(ADD_STORY, tmp_path)
    outcome = fgraph(LAND, tmp_path)
    record = tmp_path / ".fgraph"
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        [f"fgraph: error: ST-0001 cannot land: {record} is not inside a git work tree"],
    )


def test_a_land_of_a_task_exits_with_two(ready: Path) -> None:
    outcome = fgraph(["land", "T-0001", "--message", "feat: land a Task"], ready)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: 'T-0001' is no Story id: it is ST- and a number"],
    )
