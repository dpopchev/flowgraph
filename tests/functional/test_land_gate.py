"""The criterion of the gate: a landing is refused while the gate of the record fails.

The record turns the development on with `[development] gate` set to a command that fails. Run
end to end through `run` on a real git repository in a temporary directory, never a faked git;
the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run, run_gate

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
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
LAND_UNWORDED = ["land", "S-0001"]
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
FAILING = '[development]\nenabled = true\ngate = "exit 3"\n'
REFUSAL = 'S-0001 cannot land: development.gate = "exit 3" exited with status 3'
# The work of the branch is in the tree of main only once it is merged there.
SEES_THE_WORK = 'gate = "test -f work.txt"\n'
LACKS_THE_WORK = 'gate = "test ! -f work.txt"\n'
WAYS = [
    ('[development]\nenabled = true\nmerge = "merge-commit"\n', LAND),
    ('[development]\nenabled = true\nmerge = "squash"\n', LAND),
    ('[development]\nenabled = true\nmerge = "fast-forward"\n', LAND_UNWORDED),
]
WAY_IDS = ["merge-commit", "squash", "fast-forward"]
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
        run_gate=run_gate,
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
    git(checkout, "commit", "--quiet", "--message", "chore: gate the landings")
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
def gated(tmp_path: Path) -> Path:
    """The checkout of main under a gate that fails, holding a started Story ready to land."""
    return ready_to_land(tmp_path, FAILING)


class TestALandOfAStartedStoryUnderAGateThatFails:
    @pytest.fixture
    def refused(self, gated: Path) -> Landed:
        return land(LAND, gated)

    def test_land_exits_with_two_and_names_the_command_and_its_status(
        self, refused: Landed
    ) -> None:
        assert (refused.outcome.status, refused.outcome.err.splitlines()[-1:]) == (
            2,
            [f"fgraph: error: {REFUSAL}"],
        )

    def test_nothing_is_merged(self, refused: Landed, gated: Path) -> None:
        assert (git(gated, "rev-parse", "HEAD"), git(gated, "status", "--porcelain")) == (
            refused.before,
            "",
        )

    def test_the_branch_stays_where_it_was(self, refused: Landed, gated: Path) -> None:
        assert git(gated, "rev-parse", BRANCH) == refused.tip

    def test_the_worktree_of_the_branch_stays(self, refused: Landed, tmp_path: Path) -> None:
        assert (tmp_path / WORKTREE / "work.txt").is_file()

    def test_status_lists_the_story_under_in_progress_still(
        self, refused: Landed, gated: Path
    ) -> None:
        assert fgraph(["status"], gated).out == (
            f"Backlog (0)\nInProgress (1)\n  S-0001  1/1 T  {TITLE}\nCompleted (0)\n"
        )


@pytest.mark.parametrize(("config", "argv"), WAYS, ids=WAY_IDS)
def test_a_land_under_a_gate_that_fails_on_the_work_merged_leaves_main_and_the_branch(
    config: str, argv: list[str], tmp_path: Path
) -> None:
    checkout = ready_to_land(tmp_path, f"{config}{LACKS_THE_WORK}")
    refused = land(argv, checkout)
    assert (
        refused.outcome.status,
        git(checkout, "rev-parse", "HEAD"),
        git(checkout, "status", "--porcelain"),
        git(checkout, "rev-parse", BRANCH),
    ) == (2, refused.before, "", refused.tip)


@pytest.mark.parametrize(("config", "argv"), WAYS, ids=WAY_IDS)
def test_a_land_under_a_gate_that_passes_on_the_work_merged_exits_with_zero(
    config: str, argv: list[str], tmp_path: Path
) -> None:
    checkout = ready_to_land(tmp_path, f"{config}{SEES_THE_WORK}")
    assert fgraph(argv, checkout).status == 0


def test_a_land_under_a_gate_that_passes_lists_the_story_under_completed(tmp_path: Path) -> None:
    checkout = ready_to_land(tmp_path, f"{WAYS[0][0]}{SEES_THE_WORK}")
    fgraph(LAND, checkout)
    merge = git(checkout, "rev-parse", "--short", "HEAD~1")
    assert fgraph(["status"], checkout).out == (
        f"Backlog (0)\nInProgress (0)\nCompleted (1)\n  S-0001  {merge}  {TITLE}\n"
    )


def test_the_output_of_the_gate_is_written_as_the_gate_wrote_it(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    checkout = ready_to_land(tmp_path, '[development]\nenabled = true\ngate = "echo checked"\n')
    capfd.readouterr()
    fgraph(LAND, checkout)
    assert capfd.readouterr().out == "checked\n"
