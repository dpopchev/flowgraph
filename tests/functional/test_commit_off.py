"""The criterion of the commits turned off: `fgraph add story` writes the Story, uncommitted.

The record holds a `config.toml` with `[git] commit = false`. Run end to end through `run` on a
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

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0040: the configuration holds no [git] table yet"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists from 0 to 1", *CRITERION]
STORY_FILE = ".fgraph/items/S-0001.toml"
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
    """A git repository on main with one commit, holding `README` and a record with no item yet.

    The commit holds the config.toml of the record, which turns its commits off.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / "README").write_text("a project\n", encoding="utf-8")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text("[git]\ncommit = false\n", encoding="utf-8")
    git(path, "add", "README", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "first")
    return path


class TestAStoryAddedWithTheCommitsOff:
    @pytest.fixture
    def added(self, checkout: Path) -> Outcome:
        return fgraph(ADD_STORY, checkout)

    def test_add_says_the_story_is_added_and_warns_of_nothing(self, added: Outcome) -> None:
        assert added == Outcome(0, "added S-0001\n", "")

    def test_the_story_is_in_the_record_and_git_log_holds_no_new_commit(
        self, added: Outcome, checkout: Path
    ) -> None:
        shown = fgraph(["show", "S-0001"], checkout).out.splitlines()[:1]
        assert (shown, git(checkout, "log", "--format=%s")) == (
            ["S-0001  Raise the Stories fgraph lists from 0 to 1"],
            "first",
        )

    def test_the_file_of_the_story_is_left_uncommitted(
        self, added: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "status", "--porcelain", "--untracked-files=all") == (
            f"?? {STORY_FILE}"
        )
