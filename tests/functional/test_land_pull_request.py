"""The criterion of a landing through a pull request: `fgraph land` pushes the branch, then lands.

With `[development] merge = "pull-request"` the first `fgraph land` pushes the branch of the work
item to the origin and names the command that opens its pull request, completing nothing; run
again once main holds the pull request merged, it completes the work item at the commit main is
on. Run end to end through `run` on a real git repository in a temporary directory whose origin
is a bare repository beside it, the host played by a second clone; never a faked git, never a
real remote. The identity of its commits comes from the environment and no git config of the
machine is read.
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
    *("--output", "work.txt", "--check", "make test"),
]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
DEVELOPMENT = "[development]\nenabled = true\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
LAND = ["land", "S-0001"]
REQUESTED = (
    f"pushed {BRANCH} to origin\n"
    f"open its pull request: gh pr create --base main --head {BRANCH}\n"
    "S-0001 is not completed: run fgraph land S-0001 again once main holds its pull request"
    " merged\n"
)


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


@pytest.fixture
def checkout(tmp_path: Path, origin: Path) -> Path:
    """The checkout ready to land through a pull request, its main pushed to the origin."""
    path = ready(tmp_path, origin, 'merge = "pull-request"\n')
    git(path, "push", "--quiet", "origin", "main")
    return path


def branch_listed(checkout: Path) -> str:
    """The name of the branch of the work item as the checkout lists it, empty when it has none."""
    return git(checkout, "branch", "--list", "--format=%(refname:short)", BRANCH)


class TestALandingThroughAPullRequest:
    @pytest.fixture
    def before(self, checkout: Path, origin: Path) -> tuple[str, str]:
        return git(checkout, "rev-parse", "main"), git(origin, "rev-parse", "main")

    @pytest.fixture
    def requested(self, checkout: Path, before: tuple[str, str]) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_pushes_the_branch_and_names_the_pull_request_to_open(
        self, requested: Outcome
    ) -> None:
        assert requested == Outcome(0, REQUESTED, "")

    def test_the_origin_holds_the_branch_at_the_commit_of_the_worktree(
        self, requested: Outcome, origin: Path, tmp_path: Path
    ) -> None:
        assert git(origin, "rev-parse", BRANCH) == git(tmp_path / WORKTREE, "rev-parse", "HEAD")

    # The facts of what stays where it was carry the exit status too, as those of
    # tests/functional/test_land_push.py do: a landing refused leaves them as well.

    def test_main_of_the_checkout_is_where_it_was_with_nothing_to_commit(
        self, requested: Outcome, checkout: Path, before: tuple[str, str]
    ) -> None:
        main = git(checkout, "rev-parse", "main")
        assert (requested.status, main, git(checkout, "status", "--porcelain")) == (
            0,
            before[0],
            "",
        )

    def test_main_of_the_origin_is_where_it_was(
        self, requested: Outcome, origin: Path, before: tuple[str, str]
    ) -> None:
        assert (requested.status, git(origin, "rev-parse", "main")) == (0, before[1])

    def test_the_story_stays_in_progress(self, requested: Outcome, checkout: Path) -> None:
        assert fgraph(["show", "S-0001"], checkout).out.splitlines()[1] == (
            "  bucket       in-progress"
        )

    def test_the_branch_and_its_worktree_stay(
        self, requested: Outcome, checkout: Path, tmp_path: Path
    ) -> None:
        stays = (branch_listed(checkout), (tmp_path / WORKTREE).is_dir())
        assert (requested.status, *stays) == (0, BRANCH, True)

    def test_land_run_again_before_the_merge_says_the_same(
        self, requested: Outcome, checkout: Path
    ) -> None:
        assert fgraph(LAND, checkout) == Outcome(0, REQUESTED, "")


@dataclass(frozen=True)
class Landed:
    """The second landing, once main holds the pull request merged, and the commit main is on."""

    outcome: Outcome
    at: str


class TestALandingRunAgainOnceThePullRequestIsMerged:
    @pytest.fixture
    def landed(self, checkout: Path, origin: Path, tmp_path: Path) -> Landed:
        fgraph(LAND, checkout)
        host = tmp_path / "host"
        git(tmp_path, "clone", "--quiet", str(origin), str(host))
        git(
            host,
            "merge",
            "--quiet",
            "--no-ff",
            "--message",
            "Merge pull request",
            f"origin/{BRANCH}",
        )
        git(host, "push", "--quiet", "origin", "main")
        git(checkout, "pull", "--quiet", "--ff-only", "origin", "main")
        at = git(checkout, "rev-parse", "--short", "HEAD")
        return Landed(fgraph(LAND, checkout), at)

    def test_land_says_the_story_is_landed_at_the_commit_main_is_on(self, landed: Landed) -> None:
        assert landed.outcome == Outcome(
            0, f"landed S-0001 at {landed.at}\nrun: an action -> another\n", ""
        )

    def test_the_story_is_completed_at_that_commit(self, landed: Landed, checkout: Path) -> None:
        line = f"  S-0001  {landed.at}  Raise the Stories fgraph lists from 0 to 1"
        assert line in fgraph(["status"], checkout).out.splitlines()

    def test_main_holds_the_write_that_completes_the_story(
        self, landed: Landed, checkout: Path
    ) -> None:
        assert git(checkout, "log", "-1", "--format=%s", "main") == (
            "chore: complete S-0001 in the record"
        )

    def test_the_branch_and_its_worktree_are_removed(
        self, landed: Landed, checkout: Path, tmp_path: Path
    ) -> None:
        assert (branch_listed(checkout), (tmp_path / WORKTREE).exists()) == ("", False)

    def test_fgraph_made_no_merge_of_its_own(self, landed: Landed, checkout: Path) -> None:
        assert git(checkout, "log", "--merges", "--format=%s", "main") == "Merge pull request"


def test_a_land_through_a_pull_request_with_a_message_exits_with_two_naming_the_key(
    checkout: Path,
) -> None:
    outcome = fgraph([*LAND, "--message", "feat: land"], checkout)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (
        2,
        "fgraph: error: S-0001 cannot land with --message:"
        " development.merge = pull-request makes no commit to word",
    )


def test_config_show_lists_the_merge_through_a_pull_request(checkout: Path) -> None:
    assert 'development.merge = "pull-request"' in fgraph(["config", "show"], checkout).out.split(
        "\n"
    )
