"""The next Story of a Feature with the development on: the landing of the one before starts it.

The landing commits the completion and the start as one commit of the record and checks the
branch of the next Story out at it, in a worktree of its own; a next Story that cannot start
leaves the landing as it is. Run end to end through `run` on a real git repository in a
temporary directory, never a faked git; the identity of its commits comes from the environment
and no git config is read.
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
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
TASK_FOR_OTHER = [
    "add",
    "task",
    "a task title",
    "--parent",
    "S-0002",
    "--output",
    "an output",
    "--check",
    "make test",
]
ADD_ALONE = ["add", "story", "a title that stands alone", *CRITERION]
TASK_FOR_ALONE = [
    "add",
    "task",
    "a task title",
    "--parent",
    "S-0003",
    "--output",
    "an output",
    "--check",
    "make test",
]
SECOND_WITHOUT_A_TASK = (ADD_FEATURE, ADD_STORY, ADD_TASK, ADD_OTHER)
TWO_STORIES = (*SECOND_WITHOUT_A_TASK, TASK_FOR_OTHER)
LAND = ["land", "S-0001", "--message", "feat: land the first Story"]
LEAF = "S-0001-raise-the-stories-fgraph"
BRANCH = f"wi/{LEAF}"
NEXT_LEAF = "S-0002-another-title"
NEXT_BRANCH = f"wi/{NEXT_LEAF}"
STORY_FILE = ".fgraph/items/S-0001.toml"
NEXT_FILE = ".fgraph/items/S-0002.toml"
ALL_BRANCHES = ("branch", "--list", "--format=%(refname:short)", "wi/*")
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


def ready_to_land(tmp_path: Path, added: Sequence[Sequence[str]]) -> Path:
    """The checkout of main of a repository whose started Feature holds S-0001 ready to land.

    The development is on and the commits of main hold what is added. The Feature is started
    with S-0001, whose one Task is worked and completed in the worktree of its branch.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    for argv in (*added, ["start", "F-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / "project.worktrees" / LEAF
    fgraph(["start", "T-0001"], worktree)
    (worktree / "work.txt").write_text("the work of the Task\n", encoding="utf-8")
    git(worktree, "add", "work.txt")
    git(worktree, "commit", "--quiet", "--message", "feat: do the work of the Task")
    fgraph(["complete", "T-0001", "--commit", git(worktree, "rev-parse", "HEAD")], worktree)
    return checkout


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


class TestAStoryOfAStartedFeatureLandedWhileTheNextIsInBacklog:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        return ready_to_land(tmp_path, TWO_STORIES)

    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_names_the_next_story_started_then_its_branch_and_its_worktree(
        self, landed: Outcome, checkout: Path, tmp_path: Path
    ) -> None:
        merge = git(checkout, "rev-parse", "--short", "HEAD~1")
        worktree = tmp_path / "project.worktrees" / NEXT_LEAF
        assert (landed.status, landed.out) == (
            0,
            f"landed S-0001 at {merge}\nstarted S-0002\nbranch {NEXT_BRANCH} in {worktree}\n",
        )

    def test_the_complete_and_the_start_are_one_commit_of_the_record_with_the_files_of_both(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "log", "-1", "--format=%s"),
            git(checkout, "show", "--name-only", "--format=", "HEAD").splitlines(),
        ) == ("chore: complete S-0001 and start S-0002 in the record", [STORY_FILE, NEXT_FILE])

    def test_the_branch_of_the_next_story_is_at_that_commit_of_the_record(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert git(checkout, "rev-parse", NEXT_BRANCH) == git(checkout, "rev-parse", "main")

    def test_the_branch_of_the_next_story_is_the_one_left_checked_out_in_its_worktree(
        self, landed: Outcome, checkout: Path, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / NEXT_LEAF
        assert (
            git(checkout, *ALL_BRANCHES),
            git(worktree, "branch", "--show-current"),
        ) == (NEXT_BRANCH, NEXT_BRANCH)

    def test_a_task_of_the_next_story_is_started_in_its_worktree(
        self, landed: Outcome, tmp_path: Path
    ) -> None:
        worktree = tmp_path / "project.worktrees" / NEXT_LEAF
        assert fgraph(["start", "T-0002"], worktree).out == "started T-0002 of S-0002\n"

    def test_status_lists_the_next_story_started_under_the_feature(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert fgraph(["status"], checkout).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  F-0001  1/2 W  a feature title\n"
            "    S-0002  0/1 T  another title\n"
            "Completed (0)\n"
        )

    def test_nothing_is_left_to_commit(self, landed: Outcome, checkout: Path) -> None:
        assert git(checkout, "status", "--porcelain") == ""


class TestAStoryLandedWhileTheNextOfItsStartedFeatureHasNoTask:
    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = ready_to_land(tmp_path, (ADD_FEATURE, ADD_STORY, ADD_TASK))
        fgraph(ADD_OTHER, path)
        return path

    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_names_the_next_story_not_started_and_why(
        self, landed: Outcome, checkout: Path
    ) -> None:
        merge = git(checkout, "rev-parse", "--short", "HEAD~1")
        assert (landed.status, landed.out) == (
            0,
            f"landed S-0001 at {merge}\nnot started: S-0002 has no Task to start with\n",
        )

    def test_the_complete_is_committed_with_the_file_of_the_story_alone(
        self, landed: Outcome, checkout: Path
    ) -> None:
        assert (
            git(checkout, "log", "-1", "--format=%s"),
            git(checkout, "show", "--name-only", "--format=", "HEAD"),
        ) == ("chore: complete S-0001 in the record", STORY_FILE)

    def test_no_branch_is_left(self, landed: Outcome, checkout: Path) -> None:
        assert git(checkout, *ALL_BRANCHES) == ""


class TestAStoryLandedWhileAsManyWorkItemsAreStartedAsParallelStarts:
    """A Story standing alone is started beside S-0001, then `parallel` is set to 1."""

    @pytest.fixture
    def checkout(self, tmp_path: Path) -> Path:
        path = ready_to_land(tmp_path, TWO_STORIES)
        for argv in (ADD_ALONE, TASK_FOR_ALONE, ["start", "S-0003"]):
            fgraph(argv, path)
        fgraph(["config", "set", "development.parallel", "1"], path)
        return path

    @pytest.fixture
    def landed(self, checkout: Path) -> Outcome:
        return fgraph(LAND, checkout)

    def test_land_names_the_next_story_not_started_the_key_and_the_started_story(
        self, landed: Outcome, checkout: Path
    ) -> None:
        merge = git(checkout, "rev-parse", "--short", "HEAD~1")
        refusal = "S-0002 cannot start: development.parallel = 1, started already: S-0003"
        assert (landed.status, landed.out) == (
            0,
            f"landed S-0001 at {merge}\nnot started: {refusal}\n",
        )

    def test_status_lists_the_feature_in_progress_with_no_story_started_under_it(
        self, landed: Outcome, checkout: Path
    ) -> None:
        listed = fgraph(["status"], checkout).out.splitlines()
        assert [line for line in listed if "F-0001" in line or "S-0002" in line] == [
            "  F-0001  1/2 W  a feature title"
        ]


class TestAStoryOfAStartedFeatureCompletedOnItsBranchWhileTheNextIsInBacklog:
    @pytest.fixture
    def worktree(self, tmp_path: Path) -> Path:
        ready_to_land(tmp_path, TWO_STORIES)
        return tmp_path / "project.worktrees" / LEAF

    @pytest.fixture
    def refused(self, worktree: Path) -> Outcome:
        return fgraph(["complete", "S-0001", "--commit", "abc1234"], worktree)

    def test_complete_exits_with_two_naming_main_and_the_work_tree_on_it(
        self, refused: Outcome, tmp_path: Path, worktree: Path
    ) -> None:
        on_main = f"main, in {tmp_path / 'project'}"
        assert (refused.status, refused.err.splitlines()[-1]) == (
            2,
            f"fgraph: error: S-0001 completes on {on_main}: {worktree} is on {BRANCH}",
        )

    def test_nothing_is_written_on_the_branch(self, refused: Outcome, worktree: Path) -> None:
        assert (
            git(worktree, "status", "--porcelain"),
            git(worktree, "log", "-1", "--format=%s"),
        ) == (
            "",
            "chore: complete T-0001 of S-0001 in the record",
        )

    def test_its_landing_then_lands_it(self, refused: Outcome, tmp_path: Path) -> None:
        assert fgraph(LAND, tmp_path / "project").status == 0


@pytest.fixture
def on_another_branch(tmp_path: Path) -> Path:
    """The checkout on the branch `other`, its S-0001 ready to complete there, the next in Backlog.

    S-0001 is worked on main with the development off, so its record is the one of the checkout;
    the development is then turned on and the branch `other` checked out.
    """
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    (checkout / ".fgraph").mkdir()
    (checkout / "README").write_text("a project\n", encoding="utf-8")
    git(checkout, "add", "README")
    git(checkout, "commit", "--quiet", "--message", "first")
    worked = (
        ["start", "F-0001"],
        ["start", "T-0001"],
        ["complete", "T-0001", "--commit", "abc1234"],
    )
    for argv in (*TWO_STORIES, *worked, ["config", "set", "development.enabled", "true"]):
        fgraph(argv, checkout)
    git(checkout, "checkout", "--quiet", "-b", "other")
    return checkout


def test_a_completion_on_another_branch_exits_with_two_naming_main(on_another_branch: Path) -> None:
    refused = fgraph(["complete", "S-0001", "--commit", "abc1234"], on_another_branch)
    assert (refused.status, refused.err.splitlines()[-1]) == (
        2,
        f"fgraph: error: S-0001 completes on main: {on_another_branch} is on other",
    )


def test_a_completion_on_another_branch_starts_no_next_work_item_there(
    on_another_branch: Path,
) -> None:
    fgraph(["complete", "S-0001", "--commit", "abc1234"], on_another_branch)
    assert git(on_another_branch, *ALL_BRANCHES) == ""
