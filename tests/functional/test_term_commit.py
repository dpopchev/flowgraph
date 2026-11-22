"""The criterion of a term written on main: one write, one commit, which holds the term alone.

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
ADD_TERM = ["add", "term", "gate", "--means", "a check every deliverable passes"]
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
    """A git repository on main with one commit, whose record is tracked."""
    path = tmp_path / "project"
    (path / ".fgraph").mkdir(parents=True)
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph" / "config.toml").write_text("[git]\ncommit = true\n", encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "first")
    return path


class TestATermAddedOnMain:
    @pytest.fixture
    def added(self, checkout: Path) -> Outcome:
        return fgraph(ADD_TERM, checkout)

    def test_add_exits_with_zero(self, added: Outcome) -> None:
        assert added.status == 0

    def test_add_says_the_term_is_added(self, added: Outcome) -> None:
        assert added.out == "added gate\n"

    def test_the_write_is_one_commit_on_main(self, added: Outcome, checkout: Path) -> None:
        assert git(checkout, "rev-list", "--count", "main") == "2"

    def test_the_commit_says_what_was_added(self, added: Outcome, checkout: Path) -> None:
        assert (
            git(checkout, "log", "-1", "--format=%s", "main")
            == "chore: add term gate in the record"
        )

    def test_the_commit_holds_only_the_file_of_the_term(
        self, added: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "show", "--name-only", "--format=", "main") == ".fgraph/terms/gate.toml"
        )


class TestATermAddedAgain:
    @pytest.fixture
    def again(self, checkout: Path) -> Outcome:
        fgraph(ADD_TERM, checkout)
        return fgraph([*ADD_TERM[:-1], "another meaning"], checkout)

    def test_exits_with_two(self, again: Outcome) -> None:
        assert again.status == 2

    def test_names_the_term_the_record_holds_already(self, again: Outcome) -> None:
        assert again.err.endswith("fgraph: error: the record holds the term 'gate' already\n")

    def test_makes_no_commit(self, again: Outcome, checkout: Path) -> None:
        assert git(checkout, "rev-list", "--count", "main") == "2"
