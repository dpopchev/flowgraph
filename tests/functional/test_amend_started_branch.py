"""The amend of a started item with the development on: where the write is made, as one commit.

A started work item is amended in its worktree, one commit of its branch, and refused on main
naming that worktree; a started Feature is amended on main. Run end to end through `run` on a real
git repository in a temporary directory, never a faked git; the identity of its commits comes from
the environment and no git config is read.
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

XFAIL = pytest.mark.xfail(strict=True, reason="S-0145: fgraph amend refuses every started item")
NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_UNDER = [*ADD_STORY, "--parent", "F-0001"]
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
D = "the then is narrowed to one kind"
AMEND_THEN = ["amend", "S-0001", "--then", "a new state"]
AMEND_STORY = [*AMEND_THEN, "--deviation", D]
AMEND_FEATURE = ["amend", "F-0001", "--title", "another title", "--deviation", D]
NEEDED = (
    "S-0001 is started: amend it with --deviation TEXT, what changes in what it was agreed to do"
)
LEAF = "S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / LEAF
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


def refusal(outcome: Outcome) -> tuple[int, list[str]]:
    """The exit status of a run and the last line of its error output."""
    return outcome.status, outcome.err.splitlines()[-1:]


def last_commit(cwd: Path) -> tuple[str, str]:
    """The subject of the last commit of cwd and the files it changed."""
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


def started(tmp_path: Path, *argvs: Sequence[str]) -> Path:
    """The checkout of main with the development on, each command run in it in turn."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    record = path / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(path, "add", ".fgraph/config.toml")
    git(path, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in argvs:
        fgraph(argv, path)
    return path


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """The checkout of main: S-0001 with one Task, started on its worktree branch."""
    return started(tmp_path, ADD_STORY, ADD_TASK, ["start", "S-0001"])


@pytest.fixture
def worktree(checkout: Path, tmp_path: Path) -> Path:
    """The worktree of the started work item."""
    return tmp_path / WORKTREE


@XFAIL
class TestAStartedStoryAmendedInItsWorktree:
    @pytest.fixture
    def commits(self, worktree: Path) -> str:
        return git(worktree, "rev-list", "--count", "HEAD")

    @pytest.fixture
    def amended(self, commits: str, worktree: Path) -> Outcome:
        return fgraph(AMEND_STORY, worktree)

    def test_amend_exits_with_zero_and_names_the_story(self, amended: Outcome) -> None:
        assert (amended.status, amended.out) == (0, "amended S-0001\n")

    def test_the_commit_is_the_amend_with_the_file_of_the_story_alone(
        self, amended: Outcome, worktree: Path
    ) -> None:
        assert last_commit(worktree) == (
            "chore: amend S-0001 in the record",
            ".fgraph/items/S-0001.toml",
        )

    def test_the_branch_holds_one_commit_more(
        self, amended: Outcome, commits: str, worktree: Path
    ) -> None:
        assert git(worktree, "rev-list", "--count", "HEAD") == str(int(commits) + 1)


class TestAStartedStoryAmendedInTheCheckoutOfMain:
    @pytest.fixture
    def refused(self, checkout: Path) -> Outcome:
        return fgraph(AMEND_STORY, checkout)

    @XFAIL
    def test_amend_names_the_worktree_of_the_story(self, refused: Outcome, worktree: Path) -> None:
        where = f"its Tasks are written in its worktree, {worktree}"
        assert refusal(refused) == (2, [f"fgraph: error: S-0001 is started: {where}"])

    def test_nothing_is_written_on_main(self, refused: Outcome, checkout: Path) -> None:
        assert (
            git(checkout, "status", "--porcelain"),
            git(checkout, "log", "-1", "--format=%s"),
        ) == ("", "chore: start S-0001 in the record")


@XFAIL
def test_an_amend_without_a_deviation_of_a_story_on_main_is_refused(checkout: Path) -> None:
    assert refusal(fgraph(AMEND_THEN, checkout)) == (2, [f"fgraph: error: {NEEDED}"])


@XFAIL
def test_the_story_amended_in_its_worktree_is_listed_on_main_with_its_deviation(
    checkout: Path, worktree: Path
) -> None:
    fgraph(AMEND_STORY, worktree)
    shown = fgraph(["show", "S-0001"], checkout).out
    assert ("  then         a new state\n" in shown, D in shown) == (True, True)


@XFAIL
def test_the_amend_of_a_feature_on_main_is_one_commit_with_its_file_alone(tmp_path: Path) -> None:
    path = started(tmp_path, ADD_FEATURE, ADD_UNDER, ADD_TASK, ["start", "F-0001"])
    outcome = fgraph(AMEND_FEATURE, path)
    assert (outcome.status, last_commit(path)) == (
        0,
        ("chore: amend F-0001 in the record", ".fgraph/items/F-0001.toml"),
    )


@XFAIL
def test_the_amend_of_a_feature_on_the_branch_of_its_work_item_is_refused(tmp_path: Path) -> None:
    started(tmp_path, ADD_FEATURE, ADD_UNDER, ADD_TASK, ["start", "F-0001"])
    refused = fgraph(AMEND_FEATURE, tmp_path / WORKTREE)
    alone = f"the branch wi/{LEAF} writes S-0001 alone"
    assert refusal(refused) == (2, [f"fgraph: error: F-0001 is not written here: {alone}"])
