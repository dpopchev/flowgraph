"""The criterion of committing a write: `fgraph add story` leaves one commit holding its file.

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
ADD_OTHER = ["add", "story", "another title", *CRITERION]
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
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
STORY_FILE = ".fgraph/items/S-0001.toml"
OTHER_FILE = ".fgraph/items/S-0002.toml"
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


@dataclass(frozen=True)
class Step:
    """One write of the record: where it runs under tmp_path, and the commit it leaves there."""

    where: Path
    argv: tuple[str, ...]
    subject: str
    file: str


# The writes of one Story from its add to its start, then the moves of its Task in its worktree.
STEPS = (
    Step(Path("project"), tuple(ADD_STORY), "chore: add S-0001 in the record", STORY_FILE),
    Step(Path("project"), tuple(ADD_OTHER), "chore: add S-0002 in the record", OTHER_FILE),
    Step(Path("project"), tuple(ADD_TASK), "chore: add T-0001 of S-0001 in the record", STORY_FILE),
    Step(
        Path("project"),
        ("amend", "S-0002", "--then", "one more"),
        "chore: amend S-0002 in the record",
        OTHER_FILE,
    ),
    Step(
        Path("project"),
        ("reorder", "S-0002", "--before", "S-0001"),
        "chore: reorder S-0002 before S-0001 in the record",
        ".fgraph/queue.toml",
    ),
    Step(Path("project"), ("start", "S-0001"), "chore: start S-0001 in the record", STORY_FILE),
    Step(WORKTREE, ("start", "T-0001"), "chore: start T-0001 of S-0001 in the record", STORY_FILE),
    Step(
        WORKTREE,
        ("complete", "T-0001", "--commit", "3e9ae5c"),
        "chore: complete T-0001 of S-0001 in the record",
        STORY_FILE,
    ),
)


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


def last_commit(cwd: Path) -> tuple[str, str]:
    """The subject of the last commit in cwd and the files it holds."""
    return (
        git(cwd, "log", "-1", "--format=%s"),
        git(cwd, "show", "--name-only", "--format=", "HEAD"),
    )


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

    The commit holds the config.toml of the record, which turns the development on.
    """
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / "README").write_text("a project\n", encoding="utf-8")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text(
        "[development]\nenabled = true\n", encoding="utf-8"
    )
    git(path, "add", "README", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "first")
    return path


class TestAStoryAddedInsideAGitRepository:
    @pytest.fixture
    def added(self, checkout: Path) -> Outcome:
        return fgraph(ADD_STORY, checkout)

    def test_git_log_shows_one_new_commit(self, added: Outcome, checkout: Path) -> None:
        assert git(checkout, "rev-list", "--count", "HEAD") == "2"

    def test_the_commit_is_worded_by_fgraph(self, added: Outcome, checkout: Path) -> None:
        assert git(checkout, "log", "-1", "--format=%s") == "chore: add S-0001 in the record"

    def test_the_commit_holds_only_the_file_of_the_story(
        self, added: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "show", "--name-only", "--format=", "HEAD") == STORY_FILE

    def test_nothing_of_the_record_is_left_to_commit(self, added: Outcome, checkout: Path) -> None:
        assert git(checkout, "status", "--porcelain") == ""


@pytest.mark.parametrize("last", range(len(STEPS)), ids=[step.subject for step in STEPS])
def test_a_write_leaves_its_commit_holding_only_its_file(
    last: int, checkout: Path, tmp_path: Path
) -> None:
    for step in STEPS[: last + 1]:
        fgraph(step.argv, tmp_path / step.where)
    assert last_commit(tmp_path / STEPS[last].where) == (STEPS[last].subject, STEPS[last].file)


def test_a_story_completed_on_main_leaves_its_commit(checkout: Path, tmp_path: Path) -> None:
    for step in STEPS:
        fgraph(step.argv, tmp_path / step.where)
    git(checkout, "merge", "--quiet", "--no-ff", "--message", "feat: land S-0001", BRANCH)
    fgraph(["complete", "S-0001", "--commit", git(checkout, "rev-parse", "HEAD")], checkout)
    assert last_commit(checkout) == ("chore: complete S-0001 in the record", STORY_FILE)


def test_a_change_beside_the_record_stays_out_of_the_commit(checkout: Path) -> None:
    (checkout / "notes.txt").write_text("a change of the development\n", encoding="utf-8")
    git(checkout, "add", "notes.txt")
    fgraph(ADD_STORY, checkout)
    assert (git(checkout, "status", "--porcelain"), last_commit(checkout)[1]) == (
        "A  notes.txt",
        STORY_FILE,
    )


def test_a_write_that_leaves_its_file_as_it_was_makes_no_commit(checkout: Path) -> None:
    fgraph(ADD_STORY, checkout)
    fgraph(["amend", "S-0001", "--then", "another"], checkout)
    assert git(checkout, "log", "-1", "--format=%s") == "chore: add S-0001 in the record"


def test_a_write_outside_a_git_work_tree_is_made_without_a_warning(tmp_path: Path) -> None:
    outcome = fgraph(ADD_STORY, tmp_path)
    assert (outcome.status, outcome.out, outcome.err) == (0, "added S-0001\n", "")


class TestAnAddWhoseCommitGitRefuses:
    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        hook = checkout / ".git" / "hooks" / "pre-commit"
        hook.write_text("#!/bin/sh\necho refused by the hook >&2\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        return fgraph(ADD_STORY, checkout)

    def test_add_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_add_names_the_git_command_and_its_error(self, refused: Outcome) -> None:
        assert refused.err.splitlines()[-1:] == [
            "fgraph: error: git commit --quiet --only --message chore: add S-0001 in the record"
            f" -- {STORY_FILE} failed: refused by the hook"
        ]

    def test_the_file_of_the_story_is_removed_again(self, refused: Outcome, checkout: Path) -> None:
        assert not (checkout / STORY_FILE).exists()
