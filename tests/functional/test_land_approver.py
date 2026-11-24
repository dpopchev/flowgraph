"""The criterion of S-0099: under `development.approver = "developer"` `fgraph land` waits.

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
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
DEVELOPMENT = "[development]\nenabled = true\n"
HELD = (
    "fgraph: error: S-0001 cannot land: development.approver = developer, the landing waits "
    "for the developer -- run fgraph land S-0001 --approved once the developer approves it"
)
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


def last_line(text: str) -> str:
    """The last line of a text, empty when it has none."""
    lines = text.splitlines()
    return lines[-1] if lines else ""


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
    into the configuration are not, and that last commit is made only when delivery is not "".
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
    if delivery:
        config.write_text(f"{DEVELOPMENT}{delivery}", encoding="utf-8")
        git(
            checkout, "commit", "--quiet", "--message", "chore: set the delivery", "--", str(config)
        )
    return checkout


class TestALandingHeldForTheDeveloper:
    @pytest.fixture
    def checkout(self, tmp_path: Path, origin: Path) -> Path:
        return ready(tmp_path, origin, 'approver = "developer"\n')

    @pytest.fixture
    def before(self, checkout: Path) -> str:
        return git(checkout, "rev-parse", "main")

    @pytest.fixture
    def held(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_exits_with_two(self, held: Outcome) -> None:
        assert (held.status, last_line(held.err)) == (2, HELD)

    def test_land_writes_no_output(self, held: Outcome) -> None:
        assert (last_line(held.err), held.out) == (HELD, "")

    def test_nothing_is_merged_nor_written(
        self, held: Outcome, checkout: Path, before: str
    ) -> None:
        assert (
            last_line(held.err),
            git(checkout, "rev-parse", "main"),
            git(checkout, "status", "--porcelain"),
        ) == (HELD, before, "")

    def test_the_branch_and_the_story_are_as_they_were(self, held: Outcome, checkout: Path) -> None:
        assert (
            git(checkout, "branch", "--list", "--format=%(refname:short)", BRANCH),
            fgraph(["show", "S-0001"], checkout).out.splitlines()[1],
        ) == (BRANCH, "  bucket       InProgress")


class TestALandingTheDeveloperApproved:
    @pytest.fixture
    def checkout(self, tmp_path: Path, origin: Path) -> Path:
        return ready(tmp_path, origin, 'approver = "developer"\n')

    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        return fgraph([*LAND, "--approved"], checkout)

    def test_land_with_approved_lands_it(self, landed: Outcome, checkout: Path) -> None:
        assert (landed.status, landed.out.splitlines()[0]) == (
            0,
            f"landed S-0001 at {git(checkout, 'rev-parse', '--short', 'main~1')}",
        )

    def test_main_holds_the_write_that_completes_the_story(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "log", "-1", "--format=%s", "main") == (
            "chore: complete S-0001 in the record"
        )


def test_with_approver_agent_the_landing_needs_no_flag(tmp_path: Path, origin: Path) -> None:
    checkout = ready(tmp_path, origin, 'approver = "agent"\n')
    assert fgraph(LAND, checkout).status == 0


def test_with_approver_agent_the_flag_changes_nothing(tmp_path: Path, origin: Path) -> None:
    checkout = ready(tmp_path, origin, 'approver = "agent"\n')
    assert fgraph([*LAND, "--approved"], checkout).status == 0


def test_a_development_off_names_enabled_and_not_the_approver(tmp_path: Path, origin: Path) -> None:
    checkout = ready(tmp_path, origin, 'approver = "developer"\n')
    (checkout / ".fgraph" / "config.toml").write_text(
        '[development]\nenabled = false\napprover = "developer"\n',
        encoding="utf-8",
    )
    error = last_line(fgraph(LAND, checkout).err)
    assert ("development.enabled" in error, "approver" in error) == (True, False)


class TestTheKeyOfTheConfiguration:
    def test_config_show_lists_the_developer(self, tmp_path: Path, origin: Path) -> None:
        checkout = ready(tmp_path, origin, 'approver = "developer"\n')
        lines = fgraph(["config", "show"], checkout).out.splitlines()
        assert 'development.approver = "developer"' in lines

    def test_config_show_lists_the_agent_by_default(self, tmp_path: Path, origin: Path) -> None:
        checkout = ready(tmp_path, origin, "")
        lines = fgraph(["config", "show"], checkout).out.splitlines()
        assert 'development.approver = "agent"' in lines

    def test_config_set_writes_the_developer(self, tmp_path: Path, origin: Path) -> None:
        checkout = ready(tmp_path, origin, "")
        outcome = fgraph(["config", "set", "development.approver", "developer"], checkout)
        assert outcome == Outcome(0, 'set development.approver = "developer"\n', "")

    def test_a_word_that_is_neither_is_refused(self, tmp_path: Path, origin: Path) -> None:
        checkout = ready(tmp_path, origin, 'approver = "team"\n')
        outcome = fgraph(["status"], checkout)
        assert (
            outcome.status,
            last_line(outcome.err).endswith(
                'development.approver is "team": it takes agent or developer'
            ),
        ) == (2, True)


def test_without_the_key_the_landing_exits_zero(tmp_path: Path, origin: Path) -> None:
    checkout = ready(tmp_path, origin, "")
    assert fgraph(LAND, checkout).status == 0
