"""The criterion of a release of verified work: `fgraph release` asks an answer of each work item.

A Story, a Bug or an Upkeep completed since the last v* tag that holds no answer of `fgraph
verify` refuses the release, exit 2 and no tag; a Spike is never asked. Run end to end through
`run` on a real git repository in a temporary directory, never a faked git; the identity of its
commits and its tags comes from the environment and no git config of the machine is read.
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
ADD_BUG = ["add", "bug", "a bug title", "--observed", "it fails", "--expected", "it works"]
ADD_SPIKE = ["add", "spike", "a spike title", "--hypothesis", "Can one file hold it?"]
TAG_AT_CLOSE = '[development]\nenabled = true\n[delivery]\ntag = "close"\n'
CLOSING_SPIKE = ("--decision", "a decision", "--answer", "yes")
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
NOT_VERIFIED = "fgraph: error: {} not verified{}: no release -- run fgraph verify on each first"
XFAIL = pytest.mark.xfail(
    strict=True, reason="S-0149: fgraph release tags while a completed work item holds no answer"
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
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def succeeded(outcome: Outcome) -> Outcome:
    """The outcome, once it exited 0; its error output is the failure message otherwise."""
    assert outcome.status == 0, outcome.err
    return outcome


def land(checkout: Path, add: Sequence[str], *closing: str) -> None:
    """Add one work item and a Task, start, work and land it, and ask no answer of verify."""
    item = succeeded(fgraph(add, checkout)).out.split()[1]
    add_task = ["add", "task", "a task title", "--parent", item, "--output", "an output"]
    task = succeeded(fgraph([*add_task, "--check", "make test"], checkout)).out.split()[1]
    started = succeeded(fgraph(["start", item], checkout)).out.splitlines()[-1]
    worktree = Path(started.split(" in ", 1)[1])
    succeeded(fgraph(["start", task], worktree))
    (worktree / f"{item}.txt").write_text(f"the work of {item}\n", encoding="utf-8")
    git(worktree, "add", f"{item}.txt")
    git(worktree, "commit", "--quiet", "--message", f"feat: do the work of {item}")
    commit = git(worktree, "rev-parse", "HEAD")
    succeeded(fgraph(["complete", task, "--commit", commit], worktree))
    succeeded(fgraph(["land", item, "--message", f"feat: land {item}", *closing], checkout))


def tags(checkout: Path) -> str:
    """The v* tags of the checkout, one per line."""
    return git(checkout, "tag", "--list", "v*")


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
def untagged(tmp_path: Path) -> Path:
    """The checkout of main with the development turned on, no tag, nothing completed."""
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    config = checkout / ".fgraph" / "config.toml"
    config.parent.mkdir()
    config.write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    return checkout


@pytest.fixture
def tagged(untagged: Path) -> Path:
    """The checkout of main tagged v0.1.0, nothing completed."""
    git(untagged, "tag", "--annotate", "--message", "release v0.1.0", "v0.1.0")
    return untagged


class TestAReleaseWhileAStoryCompletedSinceTheLastTagIsNotVerified:
    @pytest.fixture
    def refused(self, tagged: Path) -> Outcome:
        land(tagged, ADD_STORY)
        return fgraph(["release"], tagged)

    @XFAIL
    def test_the_release_exits_with_two_naming_the_story(self, refused: Outcome) -> None:
        last = refused.err.splitlines()[-1] if refused.err else ""
        assert (refused.status, last) == (2, NOT_VERIFIED.format("S-0001", " since v0.1.0"))

    @XFAIL
    def test_no_tag_is_made(self, refused: Outcome, tagged: Path) -> None:
        assert (refused.status, tags(tagged)) == (2, "v0.1.0")

    @XFAIL
    def test_the_release_run_again_after_the_answer_tags_the_next_minor(
        self, refused: Outcome, tagged: Path
    ) -> None:
        succeeded(fgraph(["verify", "S-0001", "--yes", "it holds"], tagged))
        again = fgraph(["release"], tagged)
        assert (again.status, tags(tagged)) == (0, "v0.1.0\nv0.2.0")


@XFAIL
def test_a_bug_completed_since_the_last_tag_is_asked_as_a_story_is(tagged: Path) -> None:
    land(tagged, ADD_BUG)
    refused = fgraph(["release"], tagged)
    last = refused.err.splitlines()[-1] if refused.err else ""
    assert (refused.status, last) == (2, NOT_VERIFIED.format("B-0001", " since v0.1.0"))


@XFAIL
def test_a_story_and_an_upkeep_are_both_named_on_the_one_line(tagged: Path) -> None:
    land(tagged, ADD_STORY)
    land(tagged, ADD_UPKEEP)
    refused = fgraph(["release"], tagged)
    last = refused.err.splitlines()[-1] if refused.err else ""
    assert (refused.status, last) == (2, NOT_VERIFIED.format("S-0001, U-0001", " since v0.1.0"))


@XFAIL
def test_with_no_tag_the_line_reads_without_since(untagged: Path) -> None:
    land(untagged, ADD_STORY)
    refused = fgraph(["release"], untagged)
    last = refused.err.splitlines()[-1] if refused.err else ""
    assert (refused.status, last) == (2, NOT_VERIFIED.format("S-0001", ""))


def test_a_no_is_an_answer_and_the_release_tags(tagged: Path) -> None:
    land(tagged, ADD_STORY)
    succeeded(fgraph(["verify", "S-0001", "--no", "it fails"], tagged))
    released = fgraph(["release"], tagged)
    assert (released.status, tags(tagged)) == (0, "v0.1.0\nv0.2.0")


def test_a_spike_closes_on_its_own_answer_and_the_release_tags(tagged: Path) -> None:
    land(tagged, ADD_SPIKE, *CLOSING_SPIKE)
    released = fgraph(["release"], tagged)
    assert (released.status, tags(tagged)) == (0, "v0.1.0\nv0.1.1")


def test_the_tag_a_landing_makes_asks_for_no_answer(tagged: Path) -> None:
    land(tagged, ADD_STORY)
    config = tagged / ".fgraph" / "config.toml"
    config.write_text(TAG_AT_CLOSE, encoding="utf-8")
    git(tagged, "commit", "--quiet", "--message", "chore: tag at the landing", "--", str(config))
    land(tagged, ADD_UPKEEP)
    assert tags(tagged) == "v0.1.0\nv0.2.0"
