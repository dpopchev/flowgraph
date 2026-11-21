"""The criterion of an ignored record: `fgraph add story` writes the Story and makes no commit.

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
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
STORY_FILE = Path(".fgraph") / "items" / "ST-0001.toml"

# Every write of a record, from the add of a Story to its complete and the remove of another.
WRITES: tuple[Sequence[str], ...] = (
    ADD_STORY,
    ADD_TASK,
    ["add", "story", "another title", *CRITERION],
    ["amend", "ST-0002", "--then", "one more"],
    ["reorder", "ST-0002", "--before", "ST-0001"],
    ["start", "ST-0001"],
    ["start", "T-0001"],
    ["block", "T-0001", "--reason", "a reason", "--waiting-on", "someone"],
    ["unblock", "T-0001"],
    ["complete", "T-0001", "--commit", "3e9ae5c"],
    ["complete", "ST-0001", "--commit", "677f9b0"],
    ["remove", "ST-0002", "--reason", "a reason"],
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
def checkout(tmp_path: Path) -> Path:
    """A git repository on main with one commit, whose `.gitignore` names the record."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".gitignore").write_text(".fgraph/\n", encoding="utf-8")
    git(path, "add", ".gitignore")
    git(path, "commit", "--quiet", "--message", "first")
    return path


class TestAStoryAddedOnARecordGitIgnores:
    @pytest.fixture
    def added(self, checkout: Path) -> Outcome:
        return fgraph(ADD_STORY, checkout)

    def test_add_exits_with_zero(self, added: Outcome) -> None:
        assert added.status == 0

    def test_add_says_the_story_is_added_and_warns_of_nothing(self, added: Outcome) -> None:
        assert (added.out, added.err) == ("added ST-0001\n", "")

    def test_the_story_is_written(self, added: Outcome, checkout: Path) -> None:
        assert (checkout / STORY_FILE).is_file()

    def test_no_commit_is_made(self, added: Outcome, checkout: Path) -> None:
        assert git(checkout, "rev-list", "--count", "HEAD") == "1"


class TestAStoryStartedOnARecordGitIgnores:
    @pytest.fixture
    def started(self, checkout: Path) -> Outcome:
        fgraph(ADD_STORY, checkout)
        fgraph(ADD_TASK, checkout)
        return fgraph(["start", "ST-0001"], checkout)

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_start_says_the_story_is_started_and_names_no_branch(self, started: Outcome) -> None:
        assert started.out == "started ST-0001\n"

    def test_start_warns_that_no_branch_was_made(self, started: Outcome, checkout: Path) -> None:
        record = checkout / ".fgraph"
        assert started.err == f"fgraph: warning: no branch made: {record} is ignored by git\n"

    def test_no_branch_is_made(self, started: Outcome, checkout: Path) -> None:
        assert git(checkout, "branch", "--list", "wi/*") == ""

    def test_no_commit_is_made(self, started: Outcome, checkout: Path) -> None:
        assert git(checkout, "rev-list", "--count", "HEAD") == "1"

    def test_a_landing_is_refused_naming_that_git_ignores_the_record(
        self, started: Outcome, checkout: Path
    ) -> None:
        outcome = fgraph(["land", "ST-0001", "--message", "feat: land the Story"], checkout)
        assert (outcome.status, outcome.err.splitlines()[-1:]) == (
            2,
            [f"fgraph: error: ST-0001 cannot land: {checkout / '.fgraph'} is ignored by git"],
        )


def test_every_write_on_a_record_git_ignores_exits_with_zero(checkout: Path) -> None:
    assert [fgraph(argv, checkout).status for argv in WRITES] == [0] * len(WRITES)


def test_every_write_on_a_record_git_ignores_leaves_no_commit(checkout: Path) -> None:
    for argv in WRITES:
        fgraph(argv, checkout)
    assert git(checkout, "rev-list", "--count", "HEAD") == "1"


def test_a_story_started_off_main_on_a_record_git_ignores_is_started(checkout: Path) -> None:
    fgraph(ADD_STORY, checkout)
    fgraph(ADD_TASK, checkout)
    git(checkout, "switch", "--quiet", "--create", "a-feature")
    assert fgraph(["start", "ST-0001"], checkout).status == 0
