"""The expected of B-0023: a landing refused before main moves while main tracks no remote.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config of the machine is
read. The red tests fail until B-0023 lands; the guards pass today and after.
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
ADD_TASK = [
    *("add", "task", "a task title", "--parent", "S-0001"),
    *("--output", "an output", "--check", "make test"),
]
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
LAND_UNWORDED = ["land", "S-0001"]
BRANCHES = "wi/S-0001-*"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
DEVELOPMENT = "[development]\nenabled = true\n"
PUSH = "[delivery]\npush = true\n"
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
REFUSAL = (
    "fgraph: error: S-0001 cannot land: main tracks no branch of a remote to push to -- "
    "run git push --set-upstream <remote> main, or fgraph config set delivery.push false"
)


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


@dataclass(frozen=True)
class Refused:
    """A land of a main that tracks no branch: its checkout, its land and main's sha before."""

    checkout: Path
    land: Outcome
    before: str


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


def started(tmp_path: Path, development: str = DEVELOPMENT, delivery: str = PUSH) -> Path:
    """The checkout of main with no remote, a started Story ready to land.

    The configuration is committed before the Story starts, so main holds no commit its branch
    lacks and a fast-forward lands. The work of its one Task is committed on the worktree branch
    and the Task completed there.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    config = checkout / ".fgraph" / "config.toml"
    config.parent.mkdir()
    config.write_text(f"{development}{delivery}", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: set the configuration")
    for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    return checkout


def land_untracked(
    tmp_path: Path, development: str = DEVELOPMENT, argv: Sequence[str] = LAND
) -> Refused:
    """Land the started Story on a main that tracks no branch, with the sha main is on before it."""
    checkout = started(tmp_path, development)
    before = git(checkout, "rev-parse", "main")
    return Refused(checkout, fgraph(argv, checkout), before)


class TestALandingWhoseMainTracksNoRemote:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Refused:
        return land_untracked(tmp_path)

    def test_land_exits_with_two_and_its_last_line_names_the_missing_upstream(
        self, refused: Refused
    ) -> None:
        assert (refused.land.status, refused.land.err.splitlines()[-1:]) == (2, [REFUSAL])

    def test_show_lists_the_story_under_in_progress(self, refused: Refused) -> None:
        assert "bucket       InProgress" in fgraph(["show", "S-0001"], refused.checkout).out

    def test_the_branch_of_the_story_stands(self, refused: Refused) -> None:
        assert git(refused.checkout, "branch", "--list", BRANCHES) != ""

    def test_the_worktree_of_the_story_stands(self, tmp_path: Path, refused: Refused) -> None:
        assert (tmp_path / WORKTREE).is_dir()


@pytest.mark.parametrize(("development", "argv"), WAYS, ids=WAY_IDS)
def test_main_is_where_it_was_by_each_way(
    development: str, argv: list[str], tmp_path: Path
) -> None:
    refused = land_untracked(tmp_path, development, argv)
    assert (refused.land.status, git(refused.checkout, "rev-parse", "main")) == (2, refused.before)


def test_a_remote_main_does_not_track_is_refused_the_same(tmp_path: Path, origin: Path) -> None:
    checkout = started(tmp_path)
    git(checkout, "remote", "add", "origin", str(origin))
    landed = fgraph(LAND, checkout)
    assert (landed.status, landed.err.splitlines()[-1:]) == (2, [REFUSAL])


def test_the_same_repository_with_push_off_lands(tmp_path: Path) -> None:
    checkout = started(tmp_path, delivery="[delivery]\npush = false\n")
    landed = fgraph(LAND, checkout)
    sha = git(checkout, "rev-parse", "--short", "main~1")
    assert (landed.status, landed.out) == (0, f"landed S-0001 at {sha}\n")


def test_the_land_run_again_once_main_tracks_origin_lands_and_pushes(
    tmp_path: Path, origin: Path
) -> None:
    checkout = started(tmp_path)
    fgraph(LAND, checkout)
    git(checkout, "remote", "add", "origin", str(origin))
    git(checkout, "push", "--quiet", "--set-upstream", "origin", "main")
    again = fgraph(LAND, checkout)
    sha = git(checkout, "rev-parse", "--short", "main~1")
    assert (again.status, again.out) == (0, f"landed S-0001 at {sha}\npushed main to origin\n")
