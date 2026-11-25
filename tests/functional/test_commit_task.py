"""The criterion of S-0161: fgraph commit commits the files the brief of a started Task names.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read. The
Task is started in the worktree of its Story, where its work is.
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
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
MESSAGE = ("--message", "feat: name the files")
ON = "[development]\nenabled = true\n"
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
    try:
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
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def started_task(
    tmp_path: Path,
    output: str,
    *,
    title: str = "a title",
    description: str = "",
    start_task: bool = True,
) -> Path:
    """The worktree of a started Story whose T-0001 has the three texts, started when asked."""
    checkout = tmp_path / "project"
    record = checkout / ".fgraph"
    record.mkdir(parents=True)
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    (record / "config.toml").write_text(ON, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    add_task = ["add", "task", title, "--parent", "S-0001", "--output", output, "--check", "true"]
    if description.strip():
        add_task += ["--description", description]
    for argv in (ADD_STORY, add_task, ["start", "S-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    if start_task:
        fgraph(["start", "T-0001"], worktree)
    return worktree


def changed(where: Path, *names: str) -> None:
    """Write each file with a change and a newline, its parents made; commit nothing."""
    for name in names:
        (where / name).parent.mkdir(parents=True, exist_ok=True)
        (where / name).write_text("a change\n", encoding="utf-8")


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


NAMED = "changed: src/named.py"


def commit(cwd: Path, *argv: str) -> Outcome:
    """The outcome of fgraph commit T-0001 with the arguments, run in cwd."""
    return fgraph(["commit", "T-0001", *argv], cwd)


def last(outcome: Outcome) -> tuple[int, list[str]]:
    """The exit status of the outcome and the last line of its error output."""
    return (outcome.status, outcome.err.splitlines()[-1:])


class TestTheCommitOfAStartedTask:
    @pytest.fixture
    def worktree(self, tmp_path: Path) -> Path:
        worktree = started_task(tmp_path, "changed: src/named.py and tests/test_named.py")
        changed(worktree, "src/named.py", "tests/test_named.py")
        return worktree

    @pytest.fixture
    def committed(self, worktree: Path) -> Outcome:
        return commit(worktree, *MESSAGE)

    def test_it_exits_0(self, committed: Outcome) -> None:
        assert committed.status == 0

    def test_it_says_the_sha_of_the_commit(self, committed: Outcome, worktree: Path) -> None:
        sha = git(worktree, "rev-parse", "HEAD")
        assert committed.out == f"committed T-0001 of S-0001 at {sha}\n"

    def test_its_subject_cites_the_work_item_and_the_task(
        self, committed: Outcome, worktree: Path
    ) -> None:
        assert git(worktree, "log", "-1", "--format=%s") == "feat: name the files (S-0001, T-0001)"

    def test_it_holds_the_two_files_alone(self, committed: Outcome, worktree: Path) -> None:
        files = git(worktree, "show", "--name-only", "--format=", "HEAD").splitlines()
        assert files == ["src/named.py", "tests/test_named.py"]

    def test_it_leaves_the_work_tree_clean(self, committed: Outcome, worktree: Path) -> None:
        assert git(worktree, "status", "--porcelain") == ""


class TestTheCommitRefused:
    def test_a_changed_file_the_brief_does_not_name_refuses_the_commit(
        self, tmp_path: Path
    ) -> None:
        worktree = started_task(tmp_path, NAMED)
        changed(worktree, "src/named.py", "other.txt")
        said = (
            "fgraph: error: T-0001 cannot commit: its brief does not name other.txt -- "
            "nothing is committed; take each back or have the brief name it"
        )
        assert last(commit(worktree, *MESSAGE)) == (2, [said])

    def test_nothing_changed_refuses_the_commit(self, tmp_path: Path) -> None:
        worktree = started_task(tmp_path, NAMED)
        top = git(worktree, "rev-parse", "--show-toplevel")
        said = f"fgraph: error: T-0001 has nothing to commit: no file is changed in {top}"
        assert last(commit(worktree, *MESSAGE)) == (2, [said])

    def test_a_task_not_started_refuses_the_commit(self, tmp_path: Path) -> None:
        worktree = started_task(tmp_path, NAMED, start_task=False)
        changed(worktree, "src/named.py")
        said = (
            "fgraph: error: T-0001 is not started: "
            "fgraph commit commits the work of the Task started"
        )
        assert last(commit(worktree, *MESSAGE)) == (2, [said])

    def test_a_blank_message_refuses_the_commit(self, tmp_path: Path) -> None:
        worktree = started_task(tmp_path, NAMED)
        changed(worktree, "src/named.py")
        assert last(commit(worktree, "--message", "  ")) == (
            2,
            ["fgraph: error: message is empty"],
        )

    def test_main_refuses_the_commit_naming_the_worktree(self, tmp_path: Path) -> None:
        worktree = started_task(tmp_path, NAMED)
        changed(worktree, "src/named.py")
        said = (
            f"fgraph: error: S-0001 is started: its Tasks are written in its worktree, {worktree}"
        )
        assert last(commit(tmp_path / "project", *MESSAGE)) == (2, [said])

    def test_head_is_where_it_was_after_a_refusal(self, tmp_path: Path) -> None:
        worktree = started_task(tmp_path, NAMED)
        changed(worktree, "src/named.py", "other.txt")
        before = git(worktree, "rev-parse", "HEAD")
        commit(worktree, *MESSAGE)
        assert git(worktree, "rev-parse", "HEAD") == before
