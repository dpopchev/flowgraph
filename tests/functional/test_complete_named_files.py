"""The criterion of the named files: a Task is completed only at a commit its brief names.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read. With the
development on, `fgraph complete` of a Task at a commit that changed a file the title, the
output and the description of the Task do not name is refused (S-0142).
"""

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, open_git, read_config, run, run_gate

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
TITLE = "Raise the Stories fgraph lists from 0 to 1"
ADD_STORY = ["add", "story", TITLE, *CRITERION]
WORKTREE = Path("project.worktrees") / "S-0001-raise-the-stories-fgraph"
BRANCH = "wi/S-0001-raise-the-stories-fgraph"
ON = "[development]\nenabled = true\n"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
LINE = (
    "fgraph: error: T-0001 cannot complete: the commit {sha} changed what its brief does not "
    "name: {files}"
)
XFAIL = pytest.mark.xfail(
    strict=True, reason="S-0142: a commit that changed a file the brief does not name is taken"
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
        run_gate=run_gate,
        run_check=run_gate,
    )
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def add_task(output: str, title: str, description: str, check: str) -> list[str]:
    """The argv that adds T-0001 under S-0001, its description only when it is not blank."""
    argv = ["add", "task", title, "--parent", "S-0001", "--output", output]
    if check:
        argv += ["--check", check]
    return [*argv, "--description", description] if description.strip() else argv


def started_task(
    tmp_path: Path,
    output: str,
    *,
    title: str = "a title",
    description: str = "",
    check: str = "true",
) -> Path:
    """The worktree of a started Story that holds T-0001, started, with the texts given."""
    checkout = tmp_path / "project"
    record = checkout / ".fgraph"
    record.mkdir(parents=True)
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    (record / "config.toml").write_text(ON, encoding="utf-8")
    git(checkout, "add", ".fgraph/config.toml")
    git(checkout, "commit", "--quiet", "--message", "chore: turn the development on")
    task = add_task(output, title, description, check)
    for argv in (ADD_STORY, task, ["start", "S-0001"]):
        fgraph(argv, checkout)
    worktree = tmp_path / WORKTREE
    fgraph(["start", "T-0001"], worktree)
    return worktree


def committed(where: Path, *names: str) -> str:
    """Write each file in where, commit them together and give the sha of that commit."""
    for name in names:
        (where / name).parent.mkdir(parents=True, exist_ok=True)
        (where / name).write_text("text\n", encoding="utf-8")
        git(where, "add", name)
    git(where, "commit", "--quiet", "--message", "feat: change the files")
    return git(where, "rev-parse", "HEAD")


def complete(where: Path, sha: str, item: str = "T-0001") -> Outcome:
    """Complete the item in where at the commit given."""
    return fgraph(["complete", item, "--commit", sha], where)


def last_line(refused: Outcome) -> list[str]:
    """The last line of the error output of a run, as a list of at most one."""
    return refused.err.splitlines()[-1:]


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@XFAIL
class TestATaskCompletedAtACommitThatChangedAFileItsBriefDoesNotName:
    @pytest.fixture
    def worktree(self, tmp_path: Path) -> Path:
        return started_task(tmp_path, "changed: src/named.py")

    @pytest.fixture
    def sha(self, worktree: Path) -> str:
        return committed(worktree, "src/named.py", "other.txt")

    def test_complete_exits_with_two_and_names_the_task_the_commit_and_the_file(
        self, worktree: Path, sha: str
    ) -> None:
        refused = complete(worktree, sha)
        said = LINE.format(sha=sha, files="other.txt")
        assert (refused.status, last_line(refused)) == (2, [said])

    def test_the_branch_stays_on_the_commit_it_was_on(self, worktree: Path, sha: str) -> None:
        complete(worktree, sha)
        assert git(worktree, "rev-parse", "HEAD") == sha

    def test_the_task_stays_started(self, worktree: Path, sha: str) -> None:
        complete(worktree, sha)
        assert f"  S-0001  0/1 T  {TITLE}\n" in fgraph(["status"], worktree).out


@XFAIL
def test_every_file_the_brief_does_not_name_is_listed(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "changed: src/named.py")
    sha = committed(worktree, "src/named.py", "other.txt", "docs/more.md")
    refused = complete(worktree, sha)
    assert last_line(refused) == [LINE.format(sha=sha, files="docs/more.md, other.txt")]


@XFAIL
def test_the_check_of_the_task_is_not_run_for_a_commit_out_of_its_brief(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "changed: src/named.py", check="exit 3")
    sha = committed(worktree, "src/named.py", "other.txt")
    refused = complete(worktree, sha)
    assert last_line(refused) == [LINE.format(sha=sha, files="other.txt")]


@XFAIL
def test_a_brief_that_names_no_file_is_refused_for_the_file_changed(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "an output")
    sha = committed(worktree, "work.txt")
    refused = complete(worktree, sha)
    assert last_line(refused) == [LINE.format(sha=sha, files="work.txt")]


@XFAIL
def test_a_task_of_a_record_git_ignores_is_refused_the_same(tmp_path: Path) -> None:
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    (checkout / ".gitignore").write_text(".fgraph/\n", encoding="utf-8")
    git(checkout, "add", ".gitignore")
    git(checkout, "commit", "--quiet", "--message", "first")
    (checkout / ".fgraph").mkdir()
    (checkout / ".fgraph" / "config.toml").write_text(ON, encoding="utf-8")
    task = add_task("an output", "a title", "", "true")
    for argv in (ADD_STORY, task, ["start", "S-0001"], ["start", "T-0001"]):
        fgraph(argv, checkout)
    sha = git(checkout, "rev-parse", "HEAD")
    refused = complete(checkout, sha)
    assert (refused.status, last_line(refused)) == (
        2,
        [LINE.format(sha=sha, files=".gitignore")],
    )


@pytest.mark.parametrize(
    ("title", "output", "description"),
    [
        ("Change src/named.py", "an output", ""),
        ("a title", "changed: src/named.py", ""),
        ("a title", "an output", "the file src/named.py (12 lines)."),
    ],
    ids=["title", "output", "description"],
)
def test_a_commit_of_the_files_the_brief_names_is_completed(
    tmp_path: Path, title: str, output: str, description: str
) -> None:
    worktree = started_task(tmp_path, output, title=title, description=description)
    sha = committed(worktree, "src/named.py")
    done = complete(worktree, sha)
    assert (done.status, done.out) == (0, f"completed T-0001 of S-0001 at {sha}\n")


def test_a_file_under_a_directory_named_with_a_trailing_slash_is_completed(
    tmp_path: Path,
) -> None:
    worktree = started_task(tmp_path, "created: the tests under tests/unit/")
    sha = committed(worktree, "tests/unit/a/test_x.py")
    assert complete(worktree, sha).status == 0


def test_a_commit_of_the_record_alone_is_completed(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "an output")
    sha = git(worktree, "rev-parse", "HEAD")
    assert complete(worktree, sha).status == 0


def test_a_task_is_completed_with_the_development_off(tmp_path: Path) -> None:
    checkout = tmp_path / "project"
    checkout.mkdir()
    git(checkout, "init", "--quiet", "--initial-branch", "main")
    committed(checkout, "first.txt")
    task = add_task("an output", "a title", "", "")
    for argv in (ADD_STORY, task, ["start", "S-0001"], ["start", "T-0001"]):
        fgraph(argv, checkout)
    sha = committed(checkout, "work.txt")
    assert complete(checkout, sha).status == 0


def test_a_task_is_completed_outside_a_git_work_tree(tmp_path: Path) -> None:
    where = tmp_path / "project"
    (where / ".fgraph").mkdir(parents=True)
    (where / ".fgraph" / "config.toml").write_text(ON, encoding="utf-8")
    task = add_task("an output", "a title", "", "true")
    for argv in (ADD_STORY, task, ["start", "S-0001"], ["start", "T-0001"]):
        fgraph(argv, where)
    assert complete(where, "c6e0f15").status == 0


def test_a_work_item_completed_by_hand_is_not_asked(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "changed: work.txt")
    complete(worktree, committed(worktree, "work.txt"))
    committed(worktree, "other.txt")
    checkout = tmp_path / "project"
    git(checkout, "merge", "--quiet", "--no-ff", "--message", "feat: land S-0001", BRANCH)
    assert complete(checkout, git(checkout, "rev-parse", "HEAD"), "S-0001").status == 0


def test_a_landing_is_not_asked(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "changed: work.txt")
    complete(worktree, committed(worktree, "work.txt"))
    committed(worktree, "other.txt")
    landed = fgraph(["land", "S-0001", "--message", "feat: land S-0001"], tmp_path / "project")
    assert landed.status == 0
