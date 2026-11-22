"""The criterion of a landing pushed: with `delivery.push` true `fgraph land` pushes main.

Run end to end through `run` on a real git repository in a temporary directory whose origin is
a bare repository beside it, never a faked git; the identity of its commits comes from the
environment and no git config of the machine is read.
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
    pytest.mark.xfail(strict=True, reason="S-0090: delivery.push is not yet a key"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
DEVELOPMENT = "[development]\nenabled = true\n"
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
def origin(tmp_path: Path) -> Path:
    """A bare repository on main, the origin of the project."""
    path = tmp_path / "origin.git"
    git(tmp_path, "init", "--quiet", "--bare", "--initial-branch", "main", str(path))
    return path


def ready(tmp_path: Path, origin: Path, delivery: str) -> Path:
    """The checkout of main tracking the origin, a started Story ready to land, delivery set.

    The commit that turns the development on is pushed; the start of the Story, the work of its
    one Task, completed on its worktree branch, and the commit that writes the delivery table
    into the configuration are not.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    config = checkout / ".fgraph" / "config.toml"
    config.parent.mkdir()
    config.write_text(DEVELOPMENT, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    git(checkout, "remote", "add", "origin", str(origin))
    git(checkout, "push", "--quiet", "--set-upstream", "origin", "main")
    for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    config.write_text(f"{DEVELOPMENT}{delivery}", encoding="utf-8")
    git(checkout, "commit", "--quiet", "--message", "chore: set the delivery", "--", str(config))
    return checkout


class TestALandingWithDeliveryPushTrue:
    @pytest.fixture
    def checkout(self, tmp_path: Path, origin: Path) -> Path:
        return ready(tmp_path, origin, "[delivery]\npush = true\n")

    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_exits_with_zero(self, landed: Outcome) -> None:
        assert landed.status == 0

    def test_main_of_the_origin_is_at_main_of_the_checkout(
        self, landed: Outcome, checkout: Path, origin: Path
    ) -> None:
        assert git(origin, "rev-parse", "main") == git(checkout, "rev-parse", "main")

    def test_main_of_the_origin_holds_the_write_that_completes_the_story(
        self, landed: Outcome, origin: Path
    ) -> None:
        assert git(origin, "log", "-1", "--format=%s", "main") == (
            "chore: complete S-0001 in the record"
        )

    def test_main_of_the_origin_holds_the_merge_commit_of_the_landing(
        self, landed: Outcome, origin: Path
    ) -> None:
        assert git(origin, "log", "-1", "--format=%s", "main~1") == "feat: land the first Story"


def test_a_landing_with_delivery_push_false_leaves_the_origin_as_it_was(
    tmp_path: Path, origin: Path
) -> None:
    checkout = ready(tmp_path, origin, "[delivery]\npush = false\n")
    before = git(origin, "rev-parse", "main")
    landed = fgraph(LAND, checkout)
    assert (landed.status, git(origin, "rev-parse", "main")) == (0, before)
