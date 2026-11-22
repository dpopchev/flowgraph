"""The criterion of S-0075: fgraph about a file lists the items whose commits touched it.

Run end to end through `run` on a record in a real git repository in a temporary directory, never
a faked git; the identity of its commits comes from the environment and no git config is read.
"""

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
TITLE = "Raise the Stories fgraph lists from 0 to 1"
TASK_TITLE = "Add the listing"
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


def fgraph(argv: list[str], cwd: Path) -> Outcome:
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
        open_git=open_git,
        now=lambda: NOW,
        load_config=read_config,
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def commit(cwd: Path, name: str, message: str, *more: str) -> str:
    """Write the file of that name, commit it and the files named after it under the message.

    The sha of the commit.
    """
    (cwd / name).write_text(f"{message}\n", encoding="utf-8")
    git(cwd, "add", name, *more)
    git(cwd, "commit", "--quiet", "--message", message)
    return git(cwd, "rev-parse", "HEAD")


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
    """A git repository holding the Story S-0001 and its Task T-0001, both completed.

    The commit of the Task added `work.txt`, that of the Story changed it and added `story.txt`.
    """
    git(tmp_path, "init", "--quiet", "--initial-branch", "main")
    fgraph(["add", "story", TITLE, *CRITERION], tmp_path)
    fgraph(["add", "task", TASK_TITLE, "--parent", "S-0001", "--output", "an output"], tmp_path)
    fgraph(["start", "S-0001"], tmp_path)
    fgraph(["start", "T-0001"], tmp_path)
    task = commit(tmp_path, "work.txt", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", task], tmp_path)
    (tmp_path / "story.txt").write_text("the Story\n", encoding="utf-8")
    story = commit(tmp_path, "work.txt", "feat: land the Story", "story.txt")
    fgraph(["complete", "S-0001", "--commit", story], tmp_path)
    return tmp_path


@pytest.mark.xfail(strict=True, reason="S-0075: fgraph about does not read a path yet")
class TestAFileACommitOfATaskChanged:
    @pytest.fixture
    def about(self, checkout: Path) -> Outcome:
        return fgraph(["about", "work.txt"], checkout)

    def test_about_exits_with_zero(self, about: Outcome) -> None:
        assert about.status == 0

    def test_about_lists_the_story_with_its_commit_then_the_task_under_it(
        self, about: Outcome, checkout: Path
    ) -> None:
        task = git(checkout, "log", "--format=%H", "--grep", "the work of the Task")
        story = git(checkout, "log", "--format=%H", "--grep", "land the Story")
        assert about.out == f"S-0001  {story}  {TITLE}\n  T-0001  {task}  {TASK_TITLE}\n"
