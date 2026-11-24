"""The criterion of S-0128: a record in a folder named once, found by every command with no --dir.

Given a repository whose record lives in `.dpopchev/`, relative to its root and not tracked by git,
when `fgraph status` is run in it with no --dir, then it lists the record of that folder, named
once for the repository. Run end to end through `run` on a real git repository in a temporary
directory, never a faked git; the identity of its commits comes from the environment, and the one
git configuration read is the key `fgraph.record` of the scratch repository.
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
NAMED = ".dpopchev"
DEVELOPMENT_ON = "[development]\nenabled = true\n"
LINE = (
    "fgraph: error: git config fgraph.record names {}, which is no directory"
    " -- run fgraph init, or name another with git config fgraph.record PATH"
)
XFAIL = pytest.mark.xfail(
    strict=True, reason="S-0128: fgraph reads no key of the git configuration"
)
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
    """Run the command in cwd on its files and the real git."""
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
        make_dir=Path.mkdir,
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
def repository(tmp_path: Path) -> Path:
    """A git repository on main with one commit, whose `.git/info/exclude` names `.dpopchev/`."""
    path = tmp_path / "project"
    path.mkdir()
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / "README.md").write_text("a readme\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "--quiet", "--message", "first")
    (path / ".git" / "info").mkdir(exist_ok=True)
    (path / ".git" / "info" / "exclude").write_text(f"{NAMED}/\n", encoding="utf-8")
    return path


@pytest.fixture
def named(repository: Path) -> Path:
    """The repository with a Story in `.dpopchev/`, the folder git config fgraph.record names."""
    record = repository / NAMED
    record.mkdir()
    assert fgraph(["--dir", str(record), *ADD_STORY], repository).status == 0
    git(repository, "config", "fgraph.record", NAMED)
    return repository


@pytest.fixture
def developed(repository: Path) -> Path:
    """The repository with a Story and a Task in `.dpopchev/`, the development on, the key set."""
    record = repository / NAMED
    record.mkdir()
    (record / "config.toml").write_text(DEVELOPMENT_ON, encoding="utf-8")
    fgraph(["--dir", str(record), *ADD_STORY], repository)
    fgraph(["--dir", str(record), *ADD_TASK], repository)
    git(repository, "config", "fgraph.record", NAMED)
    return repository


@pytest.fixture
def tracked(tmp_path: Path) -> Path:
    """A repository whose record `docs/record` is tracked, the key naming it, the development on."""
    path = tmp_path / "project"
    record = path / "docs" / "record"
    record.mkdir(parents=True)
    git(path, "init", "--quiet", "--initial-branch", "main")
    (path / "README.md").write_text("a readme\n", encoding="utf-8")
    (record / "config.toml").write_text(DEVELOPMENT_ON, encoding="utf-8")
    git(path, "add", "README.md", "docs")
    git(path, "commit", "--quiet", "--message", "first")
    fgraph(["--dir", str(record), *ADD_STORY], path)
    fgraph(["--dir", str(record), *ADD_TASK], path)
    git(path, "config", "fgraph.record", "docs/record")
    return path


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """Where the worktree of the branch of the Story is checked out."""
    return tmp_path / WORKTREE


class TestARecordInTheFolderTheKeyNames:
    @XFAIL
    def test_status_with_no_dir_prints_what_status_of_the_folder_prints(self, named: Path) -> None:
        by_dir = fgraph(["--dir", str(named / NAMED), "status"], named)
        outcome = fgraph(["status"], named)
        assert (outcome.status, outcome.out) == (0, by_dir.out)

    @XFAIL
    def test_status_from_a_subdirectory_prints_the_same(self, named: Path) -> None:
        (named / "src").mkdir()
        by_dir = fgraph(["--dir", str(named / NAMED), "status"], named)
        outcome = fgraph(["status"], named / "src")
        assert (outcome.status, outcome.out) == (0, by_dir.out)

    @XFAIL
    def test_the_help_names_the_folder(self, named: Path) -> None:
        assert fgraph([], named).out.endswith(f"record: {named / NAMED}\n")

    @XFAIL
    def test_the_help_names_the_folder_with_a_fgraph_folder_beside_it(self, named: Path) -> None:
        (named / ".fgraph").mkdir()
        assert fgraph([], named).out.endswith(f"record: {named / NAMED}\n")

    @XFAIL
    def test_show_finds_the_story(self, named: Path) -> None:
        outcome = fgraph(["show", "S-0001"], named)
        assert (outcome.status, outcome.out.splitlines()[0][:6]) == (0, "S-0001")

    @XFAIL
    def test_add_writes_the_item_in_the_folder(self, named: Path) -> None:
        fgraph(ADD_OTHER, named)
        assert (named / NAMED / "items" / "S-0002.toml").is_file()

    @XFAIL
    def test_add_leaves_no_commit(self, named: Path) -> None:
        outcome = fgraph(ADD_OTHER, named)
        assert (outcome.status, git(named, "rev-list", "--count", "HEAD")) == (0, "1")

    def test_the_write_made_through_dir_was_not_committed(self, named: Path) -> None:
        assert git(named, "rev-list", "--count", "HEAD") == "1"

    def test_dir_names_another_folder_whatever_the_key_says(self, named: Path) -> None:
        (named / "other").mkdir()
        outcome = fgraph(["--dir", str(named / "other")], named)
        assert outcome.out.endswith(f"record: {named / 'other'}\n")


class TestAKeyThatNamesNoDirectory:
    @pytest.fixture
    def missing(self, repository: Path) -> Path:
        git(repository, "config", "fgraph.record", "missing")
        return repository

    @XFAIL
    def test_status_exits_with_two_naming_the_key_and_the_path(self, missing: Path) -> None:
        outcome = fgraph(["status"], missing)
        assert (outcome.status, outcome.err.splitlines()[-1]) == (
            2,
            LINE.format(missing / "missing"),
        )

    @XFAIL
    def test_status_exits_with_two_though_a_fgraph_folder_is_beside_it(self, missing: Path) -> None:
        (missing / ".fgraph").mkdir()
        outcome = fgraph(["status"], missing)
        assert (outcome.status, outcome.err.splitlines()[-1]) == (
            2,
            LINE.format(missing / "missing"),
        )


class TestInitWithTheKeySet:
    @pytest.fixture
    def keyed(self, repository: Path) -> Path:
        git(repository, "config", "fgraph.record", NAMED)
        return repository

    @XFAIL
    def test_init_names_the_folder_it_makes(self, keyed: Path) -> None:
        outcome = fgraph(["init"], keyed)
        assert (outcome.status, outcome.out) == (0, f"record: {keyed / NAMED}\n")

    @XFAIL
    def test_init_makes_the_record_in_the_folder_and_no_fgraph_folder(self, keyed: Path) -> None:
        fgraph(["init"], keyed)
        assert ((keyed / NAMED / "config.toml").is_file(), (keyed / ".fgraph").exists()) == (
            True,
            False,
        )

    @XFAIL
    def test_init_refuses_a_folder_that_is_there(self, named: Path) -> None:
        outcome = fgraph(["init"], named)
        assert (outcome.status, outcome.err.splitlines()[-1]) == (
            2,
            f"fgraph: error: {named / NAMED} holds a record already",
        )


class TestAStartOnARecordNamedAndIgnored:
    @XFAIL
    def test_start_makes_its_branch(self, developed: Path, tmp_path: Path) -> None:
        outcome = fgraph(["start", "S-0001"], developed)
        assert (outcome.status, outcome.out) == (
            0,
            f"started S-0001\nbranch {BRANCH} in {tmp_path / WORKTREE}\n",
        )

    @XFAIL
    def test_status_in_the_worktree_exits_with_two_naming_the_folder_there(
        self, developed: Path, worktree: Path
    ) -> None:
        fgraph(["start", "S-0001"], developed)
        outcome = fgraph(["status"], worktree)
        assert (outcome.status, outcome.err.splitlines()[-1]) == (
            2,
            LINE.format(worktree / NAMED),
        )


class TestAStartOnARecordNamedAndTracked:
    @pytest.fixture
    def started(self, tracked: Path) -> Outcome:
        return fgraph(["start", "S-0001"], tracked)

    @XFAIL
    def test_show_reads_its_own_copy_in_the_worktree(
        self, started: Outcome, worktree: Path
    ) -> None:
        outcome = fgraph(["show", "S-0001"], worktree)
        assert (outcome.status, outcome.out.splitlines()[0][:6]) == (0, "S-0001")

    @XFAIL
    def test_a_task_is_started_in_the_worktree(self, started: Outcome, worktree: Path) -> None:
        outcome = fgraph(["start", "T-0001"], worktree)
        assert (outcome.status, outcome.out) == (0, "started T-0001 of S-0001\n")


class TestNoKeyChangesNothing:
    def test_the_help_names_the_fgraph_folder(self, repository: Path) -> None:
        (repository / ".fgraph").mkdir()
        assert fgraph([], repository).out.endswith(f"record: {repository / '.fgraph'}\n")

    def test_no_folder_is_found_when_none_is_there(self, repository: Path) -> None:
        outcome = fgraph(["status"], repository)
        assert (outcome.status, outcome.err.splitlines()[-1]) == (
            2,
            f"fgraph: error: no .fgraph/ or fgraph/ in {repository}"
            " -- run fgraph init, or pass --dir PATH",
        )

    def test_the_help_names_the_fgraph_folder_outside_a_work_tree(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        (plain / ".fgraph").mkdir(parents=True)
        assert fgraph([], plain).out.endswith(f"record: {plain / '.fgraph'}\n")
