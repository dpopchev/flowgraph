"""The criterion of S-0150: one command merges main into the branch of a started work item.

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

XFAIL = pytest.mark.xfail(
    strict=True, reason="S-0150: fgraph has no command that merges main into a branch"
)
pytestmark = [pytest.mark.functional, XFAIL]

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
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
CONFLICT = (
    "fgraph: error: main does not merge into {branch}: conflict in {files}"
    " -- nothing is merged, the branch is as it was"
)


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
    except SystemExit as refused:  # argparse refuses a command it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def commit(cwd: Path, name: str, text: str) -> None:
    """Commit the file of that name holding the text in cwd."""
    (cwd / name).write_text(text, encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "--quiet", "--message", f"write {name}")


def turn_development_on(checkout: Path) -> None:
    """Commit `[development] enabled = true` as the config.toml of the record of the checkout."""
    record = checkout / ".fgraph"
    record.mkdir()
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")


def last_error(outcome: Outcome) -> tuple[int, list[str]]:
    """The exit status of a run and the last line of its error output."""
    return outcome.status, outcome.err.splitlines()[-1:]


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
def lane(tmp_path: Path) -> tuple[Path, Path]:
    """The checkout of main and the worktree of S-0001, started and one commit ahead of main."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    turn_development_on(path)
    for argv in (ADD_STORY, ADD_TASK, ["start", "S-0001"]):
        fgraph(argv, path)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    commit(worktree, "work.txt", "the work\n")
    return path, worktree


@pytest.fixture
def checkout(lane: tuple[Path, Path]) -> Path:
    """The checkout of main."""
    return lane[0]


@pytest.fixture
def worktree(lane: tuple[Path, Path]) -> Path:
    """The worktree of the branch of S-0001."""
    return lane[1]


@pytest.fixture
def moved(checkout: Path) -> Path:
    """The checkout after main moved: a write of the record and a commit of its own."""
    fgraph(ADD_OTHER, checkout)
    commit(checkout, "main.txt", "main\n")
    return checkout


class TestMainMergedIntoTheBranchOfAStartedStory:
    @pytest.fixture
    def before(self, moved: Path, worktree: Path) -> str:
        return git(worktree, "rev-parse", "HEAD")

    @pytest.fixture
    def synced(self, before: str, worktree: Path) -> Outcome:
        return fgraph(["sync"], worktree)

    def test_sync_prints_the_merge_at_the_short_sha_of_the_head(
        self, synced: Outcome, worktree: Path
    ) -> None:
        head = git(worktree, "rev-parse", "--short", "HEAD")
        assert (synced.status, synced.out) == (0, f"merged main into {BRANCH} at {head}\n")

    def test_the_merge_commit_is_worded_after_the_branch(
        self, synced: Outcome, worktree: Path
    ) -> None:
        assert (synced.status, git(worktree, "log", "-1", "--format=%s")) == (
            0,
            f"chore: merge main into {BRANCH}",
        )

    def test_the_merge_commit_has_the_branch_and_main_as_its_parents(
        self, synced: Outcome, before: str, worktree: Path
    ) -> None:
        parents = git(worktree, "log", "-1", "--format=%P").split()
        assert (synced.status, parents) == (0, [before, git(worktree, "rev-parse", "main")])

    def test_the_branch_is_one_merge_commit_ahead(
        self, synced: Outcome, before: str, worktree: Path
    ) -> None:
        ahead = git(worktree, "rev-list", "--count", "--first-parent", f"{before}..HEAD")
        assert (synced.status, ahead) == (0, "1")

    def test_the_branch_holds_main(self, synced: Outcome, worktree: Path) -> None:
        assert (synced.status, git(worktree, "rev-list", "--count", "HEAD..main")) == (0, "0")

    def test_the_record_of_main_is_in_the_worktree_and_nothing_is_left_uncommitted(
        self, synced: Outcome, worktree: Path
    ) -> None:
        brought = (worktree / ".fgraph" / "items" / "S-0002.toml").is_file()
        assert (synced.status, brought, git(worktree, "status", "--porcelain")) == (0, True, "")

    def test_main_is_where_it_was(self, moved: Path, worktree: Path) -> None:
        main = git(moved, "rev-parse", "main")
        assert (fgraph(["sync"], worktree).status, git(moved, "rev-parse", "main")) == (0, main)


class TestMainThatConflictsWithTheBranch:
    @pytest.fixture
    def before(self, checkout: Path, worktree: Path) -> str:
        commit(checkout, "shared.txt", "main\n")
        commit(worktree, "shared.txt", "branch\n")
        return git(worktree, "rev-parse", "HEAD")

    @pytest.fixture
    def refused(self, before: str, worktree: Path) -> Outcome:
        return fgraph(["sync"], worktree)

    def test_sync_exits_with_two_naming_the_file_in_conflict(self, refused: Outcome) -> None:
        line = CONFLICT.format(branch=BRANCH, files="shared.txt")
        assert last_error(refused) == (2, [line])

    def test_the_head_and_the_work_tree_are_as_they_were(
        self, refused: Outcome, before: str, worktree: Path
    ) -> None:
        state = (git(worktree, "rev-parse", "HEAD"), git(worktree, "status", "--porcelain"))
        line = CONFLICT.format(branch=BRANCH, files="shared.txt")
        assert (last_error(refused), state) == ((2, [line]), (before, ""))

    def test_the_file_in_conflict_reads_as_the_branch_wrote_it(
        self, refused: Outcome, worktree: Path
    ) -> None:
        text = (worktree / "shared.txt").read_text(encoding="utf-8")
        line = CONFLICT.format(branch=BRANCH, files="shared.txt")
        assert (last_error(refused), text) == ((2, [line]), "branch\n")


def test_a_second_file_in_conflict_is_named_too(checkout: Path, worktree: Path) -> None:
    for name in ("shared.txt", "a.txt"):
        commit(checkout, name, "main\n")
        commit(worktree, name, "branch\n")
    line = CONFLICT.format(branch=BRANCH, files="a.txt, shared.txt")
    assert last_error(fgraph(["sync"], worktree)) == (2, [line])


def test_sync_on_main_is_refused(checkout: Path) -> None:
    assert last_error(fgraph(["sync"], checkout)) == (
        2,
        [
            "fgraph: error: fgraph sync runs on the branch of a work item, wi/<id>-<slug>:"
            f" {checkout} is on main"
        ],
    )


def test_sync_on_a_branch_no_work_item_owns_is_refused(checkout: Path) -> None:
    git(checkout, "switch", "--quiet", "-c", "topic")
    assert last_error(fgraph(["sync"], checkout)) == (
        2,
        [
            "fgraph: error: fgraph sync runs on the branch of a work item, wi/<id>-<slug>:"
            f" {checkout} is on topic"
        ],
    )


def test_sync_with_the_development_off_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "plain"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    commit(path, "README", "a project\n")
    git(path, "switch", "--quiet", "-c", "wi/S-0001-a-slug")
    assert last_error(fgraph(["sync"], path)) == (
        2,
        [
            "fgraph: error: fgraph sync merges main into the branch of a work item:"
            " the development is off -- run fgraph config set development.enabled true"
        ],
    )


class TestAnUncommittedChange:
    @pytest.fixture
    def refused(self, moved: Path, worktree: Path) -> Outcome:
        (worktree / "work.txt").write_text("changed\n", encoding="utf-8")
        return fgraph(["sync"], worktree)

    def test_sync_is_refused_naming_the_file(self, refused: Outcome, worktree: Path) -> None:
        assert last_error(refused) == (
            2,
            [
                "fgraph: error: fgraph sync merges main into a work tree with nothing"
                f" uncommitted: {worktree} holds work.txt -- commit it first"
            ],
        )

    def test_the_change_is_still_there(self, refused: Outcome, worktree: Path) -> None:
        text = (worktree / "work.txt").read_text(encoding="utf-8")
        assert (refused.status, refused.err.endswith("commit it first\n"), text) == (
            2,
            True,
            "changed\n",
        )


def test_a_branch_that_holds_main_already_says_so(moved: Path, worktree: Path) -> None:
    fgraph(["sync"], worktree)
    again = fgraph(["sync"], worktree)
    head = git(worktree, "rev-parse", "--short", "HEAD")
    assert (again.status, again.out) == (0, f"{BRANCH} holds main already at {head}\n")


def test_a_branch_that_holds_main_already_makes_no_commit(moved: Path, worktree: Path) -> None:
    fgraph(["sync"], worktree)
    head = git(worktree, "rev-parse", "HEAD")
    again = fgraph(["sync"], worktree)
    assert (again.status, git(worktree, "rev-parse", "HEAD")) == (0, head)


def test_an_untracked_file_does_not_stop_the_merge(moved: Path, worktree: Path) -> None:
    (worktree / "notes.txt").write_text("notes\n", encoding="utf-8")
    assert fgraph(["sync"], worktree).status == 0


def test_an_untracked_file_stays_where_it_was(moved: Path, worktree: Path) -> None:
    (worktree / "notes.txt").write_text("notes\n", encoding="utf-8")
    synced = fgraph(["sync"], worktree)
    text = (worktree / "notes.txt").read_text(encoding="utf-8")
    assert (synced.status, text) == (0, "notes\n")
