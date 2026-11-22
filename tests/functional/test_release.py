"""The criterion of a release: `fgraph release` makes the next v* tag on the head of main.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits and its tags comes from the environment and no git config of
the machine is read.
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
ADD_UPKEEP = ["add", "upkeep", "Keep the Stories fgraph lists", *CRITERION]
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
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def land(checkout: Path, add: Sequence[str]) -> None:
    """Add the work item with one Task, start it, do the Task on its branch and land it."""
    item = fgraph(add, checkout).out.split()[1]
    add_task = ["add", "task", "a task title", "--parent", item, "--output", "an output"]
    task = fgraph([*add_task, "--check", "make test"], checkout).out.split()[1]
    started = fgraph(["start", item], checkout).out.splitlines()[-1]
    worktree = Path(started.split(" in ", 1)[1])
    fgraph(["start", task], worktree)
    (worktree / f"{item}.txt").write_text(f"the work of {item}\n", encoding="utf-8")
    git(worktree, "add", f"{item}.txt")
    git(worktree, "commit", "--quiet", "--message", f"feat: do the work of {item}")
    fgraph(["complete", task, "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    fgraph(["land", item, "--message", f"feat: land {item}"], checkout)


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit and tag from the environment, and no git config."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def tagged(tmp_path: Path) -> Path:
    """The checkout of main, the development turned on and tagged v0.1.0, nothing completed."""
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    config = checkout / ".fgraph" / "config.toml"
    config.parent.mkdir()
    config.write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    git(checkout, "tag", "--annotate", "--message", "release v0.1.0", "v0.1.0")
    return checkout


class TestAReleaseWithAStoryCompletedSinceTheLastTag:
    @pytest.fixture
    def released(self, tagged: Path) -> Outcome:
        land(tagged, ADD_STORY)
        return fgraph(["release"], tagged)

    def test_release_exits_with_zero(self, released: Outcome) -> None:
        assert released.status == 0

    def test_release_prints_the_next_minor_and_the_commit_it_tags(
        self, released: Outcome, tagged: Path
    ) -> None:
        assert released.out == f"tagged v0.2.0 at {git(tagged, 'rev-parse', '--short', 'main')}\n"

    def test_the_tag_is_annotated(self, released: Outcome, tagged: Path) -> None:
        assert git(tagged, "cat-file", "-t", "v0.2.0") == "tag"

    def test_the_tag_is_on_the_head_of_main(self, released: Outcome, tagged: Path) -> None:
        assert git(tagged, "rev-parse", "v0.2.0^{commit}") == git(tagged, "rev-parse", "main")


def test_a_release_with_an_upkeep_alone_completed_since_tags_the_next_patch(
    tagged: Path,
) -> None:
    land(tagged, ADD_UPKEEP)
    released = fgraph(["release"], tagged)
    assert (released.status, git(tagged, "tag", "--list", "v*")) == (0, "v0.1.0\nv0.1.1")


def test_a_release_with_nothing_completed_since_exits_with_two_and_tags_nothing(
    tagged: Path,
) -> None:
    refused = fgraph(["release"], tagged)
    assert (refused.status, git(tagged, "tag", "--list", "v*")) == (2, "v0.1.0")
