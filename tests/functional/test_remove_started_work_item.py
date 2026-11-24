"""The criterion of S-0148: a started work item is removed on main with its open Tasks.

With the development on, `fgraph remove` of a started Story, run on main, lists it under Removed
with its reason, removes its Tasks that were not completed with it and counts it no more under
development.parallel. Run end to end through `run` on a real git repository in a temporary
directory, never a faked git; the identity of its commits comes from the environment and no git
config is read.
"""

import json
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
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]


def task(parent: str) -> list[str]:
    """The command that adds a Task with a check to that work item."""
    return [
        *("add", "task", "a task title", "--parent", parent),
        *("--output", "an output", "--check", "make test"),
    ]


REMOVE = ["remove", "S-0001", "--reason", "pivoted"]
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
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
        run_check=lambda command, directory: 0,
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def turn_development_on(checkout: Path) -> None:
    """Commit the development on, one work item at once, as the config.toml of the record."""
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text(
        "[development]\nenabled = true\nparallel = 1\n", encoding="utf-8"
    )
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")


def new_checkout(path: Path, *argvs: Sequence[str]) -> Path:
    """A checkout of main at path with the development on, each command run in it in turn."""
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    turn_development_on(path)
    for argv in argvs:
        fgraph(argv, path)
    return path


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
    """The checkout of main: S-0001 with three Tasks started on its branch, S-0002 in Backlog."""
    added = (ADD_STORY, *[task("S-0001")] * 3, ADD_OTHER, task("S-0002"), ["start", "S-0001"])
    return new_checkout(tmp_path / "project", *added)


@pytest.fixture
def worktree(checkout: Path, tmp_path: Path) -> Path:
    """The worktree of the started Story."""
    return tmp_path / WORKTREE


@pytest.fixture
def worked(worktree: Path) -> str:
    """T-0001 completed at the head of the worktree and T-0002 started there: that commit."""
    fgraph(["start", "T-0001"], worktree)
    commit = git(worktree, "rev-parse", "HEAD")
    fgraph(["complete", "T-0001", "--commit", commit], worktree)
    fgraph(["start", "T-0002"], worktree)
    return commit


def task_facts(show: str) -> list[str]:
    """The words after the key of each Task line of show that names a bucket, commit or reason."""
    keys = ("    bucket", "    commit", "    reason")
    return [line.split()[-1] for line in show.splitlines() if line.startswith(keys)]


class TestAStartedStoryRemovedOnMain:
    @pytest.fixture
    def removed(self, worked: str, checkout: Path) -> Outcome:
        return fgraph(REMOVE, checkout)

    def test_remove_exits_with_zero(self, removed: Outcome) -> None:
        assert removed.status == 0

    def test_remove_says_it_and_the_branch_left(self, removed: Outcome, worktree: Path) -> None:
        assert removed.out == (
            "removed S-0001\n"
            f"left branch {BRANCH} in {worktree}: main does not hold every commit of it\n"
        )

    def test_the_branch_and_its_worktree_are_left(
        self, removed: Outcome, checkout: Path, worktree: Path
    ) -> None:
        assert (
            removed.status,
            git(checkout, "branch", "--list", BRANCH),
            worktree.is_dir(),
        ) == (0, f"+ {BRANCH}", True)

    def test_status_on_main_lists_it_under_removed(self, removed: Outcome, checkout: Path) -> None:
        assert fgraph(["status"], checkout).out == (
            "backlog (1)\n"
            "= S-0002  [1 T]  another title\n"
            "in-progress (0)\n"
            "completed (0)\n"
            "removed (1)\n"
            f"  S-0001  {TITLE}\n"
            "  pivoted\n"
        )

    def test_show_names_the_bucket_and_the_reason(self, removed: Outcome, checkout: Path) -> None:
        assert fgraph(["show", "S-0001"], checkout).out.splitlines()[1:3] == [
            "  bucket       removed",
            "  reason       pivoted",
        ]

    def test_show_keeps_the_completed_task_and_removes_the_others(
        self, removed: Outcome, worked: str, checkout: Path
    ) -> None:
        show = fgraph(["show", "S-0001"], checkout).out
        assert task_facts(show) == ["completed", worked, "removed", "pivoted", "removed", "pivoted"]

    def test_the_remove_is_one_commit_of_main_holding_its_file_alone(
        self, removed: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "log", "-1", "--format=%s"),
            git(checkout, "show", "--name-only", "--format=", "HEAD"),
            git(checkout, "status", "--porcelain"),
        ) == ("chore: remove S-0001 in the record", STORY_FILE, "")

    def test_status_json_holds_it_removed_with_its_task_states(
        self, removed: Outcome, checkout: Path
    ) -> None:
        document = json.loads(fgraph(["status", "--format", "json"], checkout).out)
        items = [item for bucket in document["buckets"] for item in bucket["items"]]
        item = next(item for item in items if item["id"] == "S-0001")
        assert (item["state"], item["reason"], [task["state"] for task in item["tasks"]]) == (
            "removed",
            "pivoted",
            ["completed", "removed", "removed"],
        )

    def test_another_story_starts_after_it(self, removed: Outcome, checkout: Path) -> None:
        outcome = fgraph(["start", "S-0002"], checkout)
        assert (outcome.status, outcome.out.splitlines()[:1]) == (0, ["started S-0002"])

    def test_its_landing_is_refused_and_main_is_unmoved(
        self, removed: Outcome, checkout: Path
    ) -> None:
        head = git(checkout, "rev-parse", "HEAD")
        outcome = fgraph(["land", "S-0001", "--message", "m"], checkout)
        assert (removed.status, outcome.status, git(checkout, "rev-parse", "HEAD")) == (0, 2, head)


def test_a_start_beside_it_is_refused_under_development_parallel(checkout: Path) -> None:
    outcome = fgraph(["start", "S-0002"], checkout)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: S-0002 cannot start: development.parallel = 1, started already: S-0001"],
    )


def test_a_story_removed_right_after_its_start_loses_its_branch_and_worktree(
    checkout: Path, worktree: Path
) -> None:
    outcome = fgraph(REMOVE, checkout)
    assert (
        outcome.out,
        git(checkout, "branch", "--list", BRANCH),
        worktree.is_dir(),
    ) == (f"removed S-0001\nremoved branch {BRANCH} in {worktree}\n", "", False)


def test_a_blocked_story_is_removed(checkout: Path, worktree: Path) -> None:
    fgraph(["block", "S-0001", "--reason", "no key", "--waiting-on", "developer"], worktree)
    outcome = fgraph(REMOVE, checkout)
    show = fgraph(["show", "S-0001"], checkout).out.splitlines()
    assert (outcome.status, show[1:3], [line for line in show if "waiting on" in line]) == (
        0,
        ["  bucket       removed", "  reason       pivoted"],
        [],
    )


def test_a_story_superseded_by_another_names_it_on_itself_and_its_tasks(
    worked: str, checkout: Path
) -> None:
    fgraph(["remove", "S-0001", "--superseded-by", "S-0002"], checkout)
    of_t2 = fgraph(["show", "S-0001"], checkout).out.split("T-0002")[1].split("T-0003")[0]
    assert (
        f"  S-0001  {TITLE}\n  superseded by S-0002\n" in fgraph(["status"], checkout).out,
        "    reason           superseded by S-0002" in of_t2,
    ) == (True, True)


def test_a_remove_run_in_the_worktree_is_refused_naming_main(
    checkout: Path, worktree: Path
) -> None:
    outcome = fgraph(REMOVE, worktree)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (
        2,
        f"fgraph: error: S-0001 is removed on main, in {checkout}: {worktree} is on {BRANCH}",
    )


def test_under_a_started_feature_no_next_work_item_starts(tmp_path: Path) -> None:
    under = ("--parent", "F-0001")
    added = (ADD_FEATURE, [*ADD_STORY, *under], task("S-0001"), [*ADD_OTHER, *under])
    feature = new_checkout(tmp_path / "feature", *added, task("S-0002"), ["start", "F-0001"])
    outcome = fgraph(REMOVE, feature)
    assert (
        outcome.out.splitlines()[:1],
        [line for line in outcome.out.splitlines() if line.startswith("started")],
        fgraph(["show", "S-0002"], feature).out.splitlines()[1],
        fgraph(["show", "F-0001"], feature).out.splitlines()[1],
    ) == (["removed S-0001"], [], "  bucket       backlog", "  bucket       in-progress")
