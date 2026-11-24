"""The criterion of a landing by squash: main gains one commit holding the work of the branch.

The record turns the development on with `[development] merge = "squash"`; beside it, a landing
by `fast-forward` and the message each way of merging takes. Run end to end through `run` on a
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
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
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
MESSAGE = "feat: land the first Story"
LAND = ["land", "S-0001", "--message", MESSAGE]
LAND_UNWORDED = ["land", "S-0001"]
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
RECORD_COMMIT = "chore: complete S-0001 in the record"
MERGE_COMMIT = '[development]\nenabled = true\nmerge = "merge-commit"\n'
SQUASH = '[development]\nenabled = true\nmerge = "squash"\n'
FAST_FORWARD = '[development]\nenabled = true\nmerge = "fast-forward"\n'
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
    """A landing run: what it left, the commit main was on before it and the tip of the branch."""

    outcome: Outcome
    before: str
    tip: str


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


def ready_to_land(tmp_path: Path, config: str) -> Path:
    """The checkout of main under that config.toml, holding a started Story ready to land.

    Its one Task is started in the worktree of its branch, the work of the Task is committed
    there and the Task is completed at that commit: the branch is three commits ahead of main.
    """
    checkout = tmp_path / "project"
    record = checkout / ".fgraph"
    record.mkdir(parents=True)
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    (record / "config.toml").write_text(config, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: say how a landing merges")
    for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    return checkout


def land(argv: Sequence[str], checkout: Path) -> Landed:
    """Run the landing in the checkout, noting where main and the branch were before it."""
    before = git(checkout, "rev-parse", "HEAD")
    tip = git(checkout, "rev-parse", BRANCH)
    return Landed(fgraph(argv, checkout), before, tip)


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
    """The checkout of main under merge = squash, holding a started Story ready to land."""
    return ready_to_land(tmp_path, SQUASH)


@pytest.fixture
def forward(tmp_path: Path) -> Path:
    """The checkout of main under merge = fast-forward, holding a started Story ready to land."""
    return ready_to_land(tmp_path, FAST_FORWARD)


class TestAStoryLandedBySquash:
    @pytest.fixture
    def landed(self, ready: Path) -> Landed:
        return land(LAND, ready)

    def test_land_exits_with_zero(self, landed: Landed) -> None:
        assert landed.outcome.status == 0

    def test_main_gains_one_commit_worded_by_the_developer_before_that_of_the_record(
        self, landed: Landed, ready: Path
    ) -> None:
        assert git(ready, "log", "--format=%s", f"{landed.before}..HEAD").splitlines() == [
            RECORD_COMMIT,
            MESSAGE,
        ]

    def test_the_one_parent_of_that_commit_is_the_commit_main_was_on(
        self, landed: Landed, ready: Path
    ) -> None:
        assert git(ready, "rev-list", "--parents", "-n", "1", "HEAD~1").split()[1:] == [
            landed.before
        ]

    def test_that_commit_holds_the_work_of_the_branch(self, landed: Landed, ready: Path) -> None:
        assert git(ready, "rev-parse", "HEAD~1^{tree}") == git(
            ready, "rev-parse", f"{landed.tip}^{{tree}}"
        )

    def test_land_names_the_story_and_that_commit(self, landed: Landed, ready: Path) -> None:
        commit = git(ready, "rev-parse", "--short", "HEAD~1")
        assert landed.outcome.out == f"landed S-0001 at {commit}\nrun: an action -> another\n"

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


class TestAStoryLandedByFastForward:
    @pytest.fixture
    def landed(self, forward: Path) -> Landed:
        return land(LAND_UNWORDED, forward)

    def test_land_exits_with_zero(self, landed: Landed) -> None:
        assert landed.outcome.status == 0

    def test_main_moves_to_the_tip_of_the_branch_before_the_commit_of_the_record(
        self, landed: Landed, forward: Path
    ) -> None:
        assert git(forward, "rev-parse", "HEAD~1") == landed.tip

    def test_main_gains_no_commit_but_that_of_the_record(
        self, landed: Landed, forward: Path
    ) -> None:
        assert git(forward, "log", "--format=%s", f"{landed.tip}..HEAD").splitlines() == [
            RECORD_COMMIT
        ]

    def test_land_names_the_story_and_the_tip_of_the_branch(
        self, landed: Landed, forward: Path
    ) -> None:
        tip = git(forward, "rev-parse", "--short", landed.tip)
        assert landed.outcome.out == f"landed S-0001 at {tip}\nrun: an action -> another\n"

    def test_status_lists_it_under_completed_with_the_tip_of_the_branch(
        self, landed: Landed, forward: Path
    ) -> None:
        tip = git(forward, "rev-parse", "--short", landed.tip)
        assert fgraph(["status"], forward).out == (
            f"Backlog (0)\nInProgress (0)\nCompleted (1)\n  S-0001  {tip}  {TITLE}\n"
        )

    def test_the_worktree_of_the_branch_is_removed(self, landed: Landed, tmp_path: Path) -> None:
        assert not (tmp_path / WORKTREE).exists()

    def test_the_branch_is_removed(self, landed: Landed, forward: Path) -> None:
        assert git(forward, "branch", "--list", "wi/*") == ""

    def test_nothing_is_left_to_commit(self, landed: Landed, forward: Path) -> None:
        assert git(forward, "status", "--porcelain") == ""


class TestALandByFastForwardOntoAMainHoldingACommitTheBranchLacks:
    @pytest.fixture
    def refused(self, forward: Path) -> Landed:
        (forward / "other.txt").write_text("other work on main\n", encoding="utf-8")
        git(forward, "add", "other.txt")
        git(forward, "commit", "--quiet", "--message", "feat: do other work on main")
        return land(LAND_UNWORDED, forward)

    def test_land_exits_with_two_and_names_the_commit_of_main(self, refused: Landed) -> None:
        assert (refused.outcome.status, refused.outcome.err.splitlines()[-1:]) == (
            2,
            [
                "fgraph: error: S-0001 cannot land by fast-forward:"
                f" main holds a commit {BRANCH} lacks"
                f" -- rebase {BRANCH} on main or merge main into it"
            ],
        )

    def test_nothing_is_merged(self, refused: Landed, forward: Path) -> None:
        assert (git(forward, "rev-parse", "HEAD"), git(forward, "status", "--porcelain")) == (
            refused.before,
            "",
        )

    def test_the_branch_stays_where_it_was(self, refused: Landed, forward: Path) -> None:
        assert git(forward, "rev-parse", BRANCH) == refused.tip


@pytest.mark.parametrize(
    ("config", "word"),
    [(MERGE_COMMIT, "merge-commit"), (SQUASH, "squash")],
    ids=["merge-commit", "squash"],
)
def test_a_land_that_makes_a_commit_exits_with_two_without_a_message_and_names_it(
    config: str, word: str, tmp_path: Path
) -> None:
    outcome = fgraph(LAND_UNWORDED, ready_to_land(tmp_path, config))
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        [
            "fgraph: error: S-0001 cannot land without --message:"
            f" development.merge = {word} makes a commit to word"
        ],
    )


def test_a_land_by_fast_forward_exits_with_two_with_a_message_and_names_it(forward: Path) -> None:
    outcome = fgraph(LAND, forward)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        [
            "fgraph: error: S-0001 cannot land with --message:"
            " development.merge = fast-forward makes no commit to word"
        ],
    )


def test_a_land_by_fast_forward_refused_with_a_message_merges_nothing(forward: Path) -> None:
    refused = land(LAND, forward)
    assert (git(forward, "rev-parse", "HEAD"), git(forward, "rev-parse", BRANCH)) == (
        refused.before,
        refused.tip,
    )
