"""The note of a Feature with the development on: written on main alone, as one commit.

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
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "Raise the Stories fgraph lists", *CRITERION, "--parent", "F-0001"]
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
NOTE = ["note", "F-0001", "--finding", "the budget is not agreed"]
LEAF = "S-0001-raise-the-stories-fgraph"
FEATURE_FILE = ".fgraph/items/F-0001.toml"
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
    """The checkout of main of a repository with the development on, S-0001 of F-0001 started."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    record = path / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in (ADD_FEATURE, ADD_STORY, ADD_TASK, ["start", "F-0001"]):
        fgraph(argv, path)
    return path


def test_the_note_of_a_feature_on_main_is_one_commit_with_its_file_alone(checkout: Path) -> None:
    fgraph(NOTE, checkout)
    assert (
        git(checkout, "log", "-1", "--format=%s"),
        git(checkout, "show", "--name-only", "--format=", "HEAD"),
    ) == ("chore: note F-0001 in the record", FEATURE_FILE)


def test_the_note_of_a_feature_on_the_branch_of_its_story_is_refused(
    checkout: Path, tmp_path: Path
) -> None:
    refused = fgraph(NOTE, tmp_path / "project.worktrees" / LEAF)
    alone = f"the branch wi/{LEAF} writes S-0001 alone"
    assert (refused.status, refused.err.splitlines()[-1:]) == (
        2,
        [f"fgraph: error: F-0001 is not written here: {alone}"],
    )
