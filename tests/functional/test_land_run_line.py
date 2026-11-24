"""The criterion of S-0151: `fgraph land` prints the criterion to run on main after landed.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config of the machine is
read.
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
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
ADD_UPKEEP = ["add", "upkeep", "Keep the Stories fgraph lists", *CRITERION]
ADD_BUG = ["add", "bug", "a bug title", "--observed", "it fails", "--expected", "it works"]
ADD_SPIKE = ["add", "spike", "a spike title", "--hypothesis", "Can one file hold it?"]
ADD_WRAPPED = [
    "add",
    "story",
    "a story title",
    "--given",
    "a state",
    "--when",
    "an action\n  over two lines",
    "--then",
    "another",
]
RUN = "run: an action -> another"
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


def landed(checkout: Path, add: Sequence[str], *closing: str) -> Outcome:
    """Add the work item with one Task, start it, do the Task on its branch and land it.

    The closing arguments go to fgraph land after its message: a Spike takes its decision.
    """
    item = fgraph(add, checkout).out.split()[1]
    add_task = ["add", "task", "a task title", "--parent", item, "--output", f"{item}.txt"]
    task = fgraph([*add_task, "--check", "make test"], checkout).out.split()[1]
    started = fgraph(["start", item], checkout).out.splitlines()[-1]
    worktree = Path(started.split(" in ", 1)[1])
    fgraph(["start", task], worktree)
    (worktree / f"{item}.txt").write_text(f"the work of {item}\n", encoding="utf-8")
    git(worktree, "add", f"{item}.txt")
    git(worktree, "commit", "--quiet", "--message", f"feat: do the work of {item}")
    fgraph(["complete", task, "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    return fgraph(["land", item, "--message", f"feat: land {item}", *closing], checkout)


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
def project(tmp_path: Path) -> Path:
    """The checkout of main with the development turned on, nothing added yet."""
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    config = checkout / ".fgraph" / "config.toml"
    config.parent.mkdir()
    config.write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    return checkout


class TestAStoryLanded:
    @pytest.fixture
    def landing(self, project: Path) -> Outcome:
        return landed(project, ADD_STORY)

    def test_the_output_names_the_story_and_the_criterion_to_run(
        self, landing: Outcome, project: Path
    ) -> None:
        merge = git(project, "rev-parse", "--short", "HEAD~1")
        assert landing.out == f"landed S-0001 at {merge}\n{RUN}\n"

    def test_the_second_line_is_the_run_line(self, landing: Outcome) -> None:
        assert (landing.status, landing.out.splitlines()[1]) == (0, RUN)


def test_an_upkeep_landed_prints_its_run_line_second(project: Path) -> None:
    upkeep = landed(project, ADD_UPKEEP)
    assert (upkeep.status, upkeep.out.splitlines()[1]) == (0, RUN)


def test_a_bug_landed_prints_its_expected_as_the_run_line(project: Path) -> None:
    bug = landed(project, ADD_BUG)
    assert (bug.status, bug.out.splitlines()[1]) == (0, "run: it works")


def test_a_when_over_two_lines_is_printed_on_one(project: Path) -> None:
    wrapped = landed(project, ADD_WRAPPED)
    assert (wrapped.status, wrapped.out.splitlines()[1]) == (
        0,
        "run: an action over two lines -> another",
    )


def test_a_spike_landed_with_its_decision_prints_no_run_line(project: Path) -> None:
    spike = landed(project, ADD_SPIKE, "--decision", "a decision", "--answer", "yes")
    merge = git(project, "rev-parse", "--short", "HEAD~1")
    assert spike.out == f"landed Q-0001 at {merge}\n"


def test_a_story_completed_on_main_prints_only_the_completed_line(project: Path) -> None:
    fgraph(ADD_STORY, project)
    add_task = ["add", "task", "a task title", "--parent", "S-0001", "--output", "work.txt"]
    fgraph([*add_task, "--check", "make test"], project)
    started = fgraph(["start", "S-0001"], project).out.splitlines()[-1]
    worktree = Path(started.split(" in ", 1)[1])
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work")
    work = git(worktree, "rev-parse", "HEAD")
    fgraph(["complete", "T-0001", "--commit", work], worktree)
    git(project, "merge", "--quiet", "--ff-only", "wi/S-0001-raise-the-stories-fgraph")
    head = git(worktree, "rev-parse", "HEAD")
    completed = fgraph(["complete", "S-0001", "--commit", head], project)
    assert completed.out == f"completed S-0001 at {head}\n"
