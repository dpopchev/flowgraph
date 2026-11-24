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

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
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
STORY_FILE = Path(".fgraph") / "items" / "S-0001.toml"

# Every write of a record, from the add of a Story to its complete and the remove of another.
WRITES: tuple[Sequence[str], ...] = (
    ADD_STORY,
    ADD_TASK,
    ["add", "story", "another title", *CRITERION],
    ["amend", "S-0002", "--then", "one more"],
    ["reorder", "S-0002", "--before", "S-0001"],
    ["start", "S-0001"],
    ["start", "T-0001"],
    ["block", "T-0001", "--reason", "a reason", "--waiting-on", "someone"],
    ["unblock", "T-0001"],
    ["complete", "T-0001", "--commit", "HEAD"],
    ["complete", "S-0001", "--commit", "HEAD"],
    ["remove", "S-0002", "--reason", "a reason"],
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
def checkout(tmp_path: Path) -> Path:
    """A git repository on main with one commit, whose `.gitignore` names the record.

    The config.toml of the record turns the development on, ignored as the rest of it.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".gitignore").write_text(".fgraph/\n", encoding="utf-8")
    git(path, "add", ".gitignore")
    git(path, "commit", "--quiet", "--message", "first")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text(
        "[development]\nenabled = true\n", encoding="utf-8"
    )
    return path


class TestAStoryAddedOnARecordGitIgnores:
    @pytest.fixture
    def added(self, checkout: Path) -> Outcome:
        return fgraph(ADD_STORY, checkout)

    def test_add_exits_with_zero(self, added: Outcome) -> None:
        assert added.status == 0

    def test_add_says_the_story_is_added_and_warns_of_nothing(self, added: Outcome) -> None:
        assert (added.out, added.err) == ("added S-0001\n", "")

    def test_the_story_is_written(self, added: Outcome, checkout: Path) -> None:
        assert (checkout / STORY_FILE).is_file()

    def test_no_commit_is_made(self, added: Outcome, checkout: Path) -> None:
        assert git(checkout, "rev-list", "--count", "HEAD") == "1"


def write(argv: Sequence[str], checkout: Path) -> Outcome:
    """Run the write in the checkout, its word HEAD replaced by the commit that is HEAD there."""
    head = git(checkout, "rev-parse", "HEAD")
    return fgraph([head if word == "HEAD" else word for word in argv], checkout)


def test_every_write_on_a_record_git_ignores_exits_with_zero(checkout: Path) -> None:
    assert [write(argv, checkout).status for argv in WRITES] == [0] * len(WRITES)


def test_every_write_on_a_record_git_ignores_leaves_no_commit(checkout: Path) -> None:
    for argv in WRITES:
        write(argv, checkout)
    assert git(checkout, "rev-list", "--count", "HEAD") == "1"
