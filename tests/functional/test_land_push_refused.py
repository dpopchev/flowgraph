"""The criterion of a push refused: the work item stays started and merged, and a land takes it up.

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


def ready(tmp_path: Path, origin: Path, delivery: str, development: str = DEVELOPMENT) -> Path:
    """The checkout of main tracking the origin, a started Story ready to land.

    The configuration, the development table and the delivery table, is committed and pushed
    before the Story starts, so main holds no commit its branch lacks and a fast-forward lands.
    The work of its one Task is committed on the worktree branch and the Task completed there.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    config = checkout / ".fgraph" / "config.toml"
    config.parent.mkdir()
    config.write_text(f"{development}{delivery}", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: set the configuration")
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
    return checkout


@dataclass(frozen=True)
class Refused:
    """A landing whose push the origin refused: the checkout, the land and the sha main is on."""

    checkout: Path
    land: Outcome
    sha: str


def refused_land(tmp_path: Path, origin: Path, development: str, argv: Sequence[str]) -> Refused:
    """Land the Story while the url of origin names no repository."""
    checkout = ready(tmp_path, origin, PUSH, development)
    git(checkout, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    landed = fgraph(argv, checkout)
    return Refused(checkout, landed, git(checkout, "rev-parse", "--short", "main"))


def taken_up(tmp_path: Path, origin: Path, development: str, argv: Sequence[str]) -> Refused:
    """The land run again once the url of origin is put back; the sha is that of the first."""
    refused = refused_land(tmp_path, origin, development, argv)
    git(refused.checkout, "remote", "set-url", "origin", str(origin))
    return Refused(refused.checkout, fgraph(argv, refused.checkout), refused.sha)


class TestALandingWhosePushIsRefused:
    @pytest.fixture
    def refused(self, tmp_path: Path, origin: Path) -> Refused:
        return refused_land(tmp_path, origin, DEVELOPMENT, LAND)

    def test_show_lists_the_story_under_in_progress(self, refused: Refused) -> None:
        assert "bucket       in-progress" in fgraph(["show", "S-0001"], refused.checkout).out

    def test_main_is_on_the_merge_with_no_commit_of_the_record_after_it(
        self, refused: Refused
    ) -> None:
        assert git(refused.checkout, "log", "-1", "--format=%s", "main") == (
            "feat: land the first Story"
        )

    def test_the_branch_stands(self, refused: Refused) -> None:
        assert git(refused.checkout, "branch", "--list", BRANCHES) != ""

    def test_land_exits_with_two_and_the_error_ends_naming_the_merge_and_the_way_back(
        self, refused: Refused
    ) -> None:
        said = f"-- main is not pushed -- S-0001 is merged at {refused.sha} and not completed"
        ending = f"{said} -- run fgraph land S-0001 again\n"
        assert (refused.land.status, refused.land.err.endswith(ending)) == (2, True)


class TestTheLandingTakenUpOnceTheOriginIsBack:
    @pytest.fixture
    def again(self, tmp_path: Path, origin: Path) -> Refused:
        refused = refused_land(tmp_path, origin, DEVELOPMENT, LAND)
        git(refused.checkout, "remote", "set-url", "origin", str(origin))
        return Refused(refused.checkout, fgraph(LAND, refused.checkout), refused.sha)

    def test_land_exits_with_zero_saying_it_landed_and_pushed(self, again: Refused) -> None:
        assert (again.land.status, again.land.out) == (
            0,
            f"landed S-0001 at {again.sha}\nrun: an action -> another\npushed main to origin\n",
        )

    def test_land_exits_with_zero_and_show_lists_the_story_under_completed(
        self, again: Refused
    ) -> None:
        shown = fgraph(["show", "S-0001"], again.checkout).out
        assert (again.land.status, "bucket       completed" in shown) == (0, True)

    def test_main_of_the_origin_is_main_of_the_checkout(self, again: Refused, origin: Path) -> None:
        assert git(origin, "rev-parse", "main") == git(again.checkout, "rev-parse", "main")

    def test_main_of_the_origin_holds_the_write_that_completes_the_story(
        self, again: Refused, origin: Path
    ) -> None:
        assert git(origin, "log", "-1", "--format=%s", "main") == (
            "chore: complete S-0001 in the record"
        )

    def test_land_exits_with_zero_and_no_branch_of_the_story_is_left(self, again: Refused) -> None:
        left = git(again.checkout, "branch", "--list", BRANCHES)
        assert (again.land.status, left) == (0, "")


@pytest.mark.parametrize(("development", "argv"), WAYS, ids=WAY_IDS)
def test_a_landing_taken_up_completes_by_each_way(
    development: str, argv: list[str], tmp_path: Path, origin: Path
) -> None:
    again = taken_up(tmp_path, origin, development, argv)
    assert (again.land.status, again.land.out) == (
        0,
        f"landed S-0001 at {again.sha}\nrun: an action -> another\npushed main to origin\n",
    )


class TestAStoryWhoseBranchIsMergedByHand:
    @pytest.fixture
    def landed(self, tmp_path: Path, origin: Path) -> Refused:
        checkout = ready(tmp_path, origin, "")
        branch = git(checkout, "branch", "--list", BRANCHES, "--format=%(refname:short)")
        git(checkout, "merge", "--no-ff", "--quiet", "--message", "feat: merge by hand", branch)
        sha = git(checkout, "rev-parse", "--short", "HEAD")
        return Refused(checkout, fgraph(LAND, checkout), sha)

    def test_land_exits_with_zero_at_the_commit_main_is_on(self, landed: Refused) -> None:
        out = f"landed S-0001 at {landed.sha}\nrun: an action -> another\n"
        assert (landed.land.status, landed.land.out) == (0, out)

    def test_show_lists_the_story_under_completed(self, landed: Refused) -> None:
        assert "bucket       completed" in fgraph(["show", "S-0001"], landed.checkout).out
