"""The expected of B-0022: a failed `fgraph init` leaves no `.fgraph/`, and a second one makes it.

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
    """Run the command in cwd on its files and the real git, making the record through make_dir."""
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        open_git=open_git,
        now=lambda: NOW,
        load_config=read_config,
        make_dir=Path.mkdir,
        remove_dir=Path.rmdir,
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
def repository(tmp_path: Path) -> Path:
    """A git repository on main with one commit, holding `README` and no record."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / "README").write_text("a project\n", encoding="utf-8")
    git(path, "add", "README")
    git(path, "commit", "--quiet", "--message", "first")
    return path


def refuse_commits(repository: Path) -> Path:
    """Install a pre-commit hook of the repository that refuses every commit; return its path."""
    hook = repository / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho refused by the hook >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    return hook


class TestAnInitWhoseCommitGitRefuses:
    @pytest.fixture
    def refused(self, repository: Path) -> Outcome:
        refuse_commits(repository)
        return fgraph(["init"], repository)

    def test_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_prints_nothing_on_stdout(self, refused: Outcome) -> None:
        assert refused.out == ""

    def test_ends_its_error_with_the_refusal_of_git(self, refused: Outcome) -> None:
        assert refused.err.splitlines()[-1:] == [
            "fgraph: error: git commit --quiet --only --message chore: make the record -- "
            ".fgraph/config.toml failed: refused by the hook"
        ]

    def test_makes_no_commit(self, refused: Outcome, repository: Path) -> None:
        assert git(repository, "rev-list", "--count", "HEAD") == "1"

    def test_leaves_git_status_nothing_to_list(self, refused: Outcome, repository: Path) -> None:
        assert git(repository, "status", "--porcelain") == ""

    def test_leaves_no_dot_directory_behind(self, refused: Outcome, repository: Path) -> None:
        assert not (repository / ".fgraph").exists()


class TestAnInitAfterOneGitRefused:
    @pytest.fixture
    def second(self, repository: Path) -> Outcome:
        hook = refuse_commits(repository)
        fgraph(["init"], repository)
        hook.unlink()
        return fgraph(["init"], repository)

    def test_exits_with_zero(self, second: Outcome) -> None:
        assert second.status == 0

    def test_prints_the_record_it_made(self, second: Outcome, repository: Path) -> None:
        assert second.out == f"record: {repository / '.fgraph'}\n"

    def test_commits_the_record_alone(self, second: Outcome, repository: Path) -> None:
        assert (
            git(repository, "log", "-1", "--format=%s"),
            git(repository, "show", "--name-only", "--format=", "HEAD"),
        ) == ("chore: make the record", ".fgraph/config.toml")


def test_an_init_that_worked_keeps_its_config_tracked(repository: Path) -> None:
    fgraph(["init"], repository)
    assert git(repository, "ls-files", ".fgraph") == ".fgraph/config.toml"
