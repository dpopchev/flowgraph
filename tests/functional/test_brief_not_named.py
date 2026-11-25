"""The criterion of S-0153: fgraph brief --not-named lists the files the brief does not name.

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


def not_named(cwd: Path, *argv: str) -> Outcome:
    """The outcome of fgraph brief S-0001 --not-named with the arguments, run in cwd."""
    return fgraph(["brief", "S-0001", "--not-named", *argv], cwd)


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The identity of every commit from the environment, and no git config of the machine."""
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    empty = tmp_path / "gitconfig"
    empty.touch()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


class TestTheFilesChangedThatTheBriefDoesNotName:
    @pytest.fixture
    def worktree(self, tmp_path: Path) -> Path:
        worktree = started_task(tmp_path, "changed: src/named.py")
        changed(worktree, "src/named.py", "other.txt")
        return worktree

    def test_it_lists_the_file_the_brief_does_not_name_and_not_the_one_it_names(
        self, worktree: Path
    ) -> None:
        listed = not_named(worktree)
        assert (listed.status, listed.out) == (0, "other.txt\n")

    def test_run_on_main_it_lists_the_files_of_the_worktree(
        self, worktree: Path, tmp_path: Path
    ) -> None:
        assert not_named(tmp_path / "project").out == "other.txt\n"

    def test_with_format_json_it_prints_a_json_list(self, worktree: Path) -> None:
        assert not_named(worktree, "--format", "json").out == '["other.txt"]\n'

    def test_it_writes_nothing(self, worktree: Path) -> None:
        before = (git(worktree, "rev-parse", "HEAD"), git(worktree, "status", "--porcelain"))
        not_named(worktree)
        assert (
            git(worktree, "rev-parse", "HEAD"),
            git(worktree, "status", "--porcelain"),
        ) == before

    def test_the_brief_without_the_option_prints_as_before(self, worktree: Path) -> None:
        shown = fgraph(["show", "S-0001"], worktree).out
        brief = fgraph(["brief", "S-0001"], worktree)
        assert (brief.status, brief.out.startswith(shown)) == (0, True)


def test_a_tracked_file_changed_a_staged_file_and_a_new_file_are_listed_by_path(
    tmp_path: Path,
) -> None:
    worktree = started_task(tmp_path, "an output")
    changed(worktree, "notes.md")
    git(worktree, "add", "notes.md")
    git(worktree, "commit", "--quiet", "--message", "docs: add notes")
    (worktree / "notes.md").write_text("a change\nanother\n", encoding="utf-8")
    changed(worktree, "staged.txt")
    git(worktree, "add", "staged.txt")
    changed(worktree, "new.txt")
    assert not_named(worktree).out == "new.txt\nnotes.md\nstaged.txt\n"


def test_a_file_under_a_directory_named_with_a_trailing_slash_is_not_listed(
    tmp_path: Path,
) -> None:
    worktree = started_task(tmp_path, "created: the tests under tests/unit/")
    changed(worktree, "tests/unit/a/test_x.py", "other.txt")
    assert not_named(worktree).out == "other.txt\n"


@pytest.mark.parametrize(
    ("title", "description"),
    [
        pytest.param("Change src/named.py", "", id="title"),
        pytest.param("a title", "the file src/named.py (12 lines).", id="description"),
    ],
)
def test_a_file_named_by_the_title_or_the_description_is_not_listed(
    tmp_path: Path, title: str, description: str
) -> None:
    worktree = started_task(tmp_path, "an output", title=title, description=description)
    changed(worktree, "src/named.py", "other.txt")
    assert not_named(worktree).out == "other.txt\n"


def test_a_file_of_the_record_is_not_listed(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "an output")
    config = worktree / ".fgraph" / "config.toml"
    config.write_text(config.read_text(encoding="utf-8") + "# a note\n", encoding="utf-8")
    changed(worktree, "other.txt")
    assert not_named(worktree).out == "other.txt\n"


def test_a_clean_worktree_lists_nothing(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "an output")
    listed = not_named(worktree)
    assert (listed.status, listed.out) == (0, "")


def test_a_work_item_with_no_started_task_is_refused(tmp_path: Path) -> None:
    worktree = started_task(tmp_path, "an output", start_task=False)
    refused = not_named(worktree)
    said = (
        "fgraph: error: S-0001 has no started Task: --not-named reads the brief of the Task started"
    )
    assert (refused.status, refused.err.splitlines()[-1:]) == (2, [said])


def test_a_record_outside_a_git_work_tree_is_refused(tmp_path: Path) -> None:
    add_task = ["add", "task", "a title", "--parent", "S-0001", "--output", "an output"]
    for argv in (ADD_STORY, add_task, ["start", "S-0001"], ["start", "T-0001"]):
        fgraph(argv, tmp_path)
    refused = not_named(tmp_path)
    said = (
        "fgraph: error: S-0001 has no files changed to read: "
        "the record is not inside a git work tree"
    )
    assert (refused.status, refused.err.splitlines()[-1:]) == (2, [said])
