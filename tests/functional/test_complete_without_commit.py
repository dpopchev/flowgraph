"""The criterion of the development off: a Story is completed without a commit.

A record that holds no `config.toml` has the development off, so the commit is no evidence of
it: `fgraph complete` takes none, of a Task as of the Story. With the development on it needs
one. Run end to end through `run` on a record in a temporary directory, through the file
adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = [
    "add",
    "task",
    "a task title",
    "--parent",
    "S-0001",
    "--output",
    "an output",
]
CHECKED_TASK = [*ADD_TASK, "--check", "make test"]
STARTED = [ADD_STORY, ADD_TASK, ["start", "S-0001"], ["start", "T-0001"]]
STARTED_CHECKED = [ADD_STORY, CHECKED_TASK, ["start", "S-0001"], ["start", "T-0001"]]
TASK_DONE = ["complete", "T-0001"]
STORY_DONE = ["complete", "S-0001"]
TASK_DONE_IN_A_COMMIT = [*TASK_DONE, "--commit", "abc1234"]
NEEDED = "is completed with --commit: the development is on, development.enabled = true"


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on its files and its configuration."""
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
        open_git=lambda _: None,
        now=lambda: NOW,
        load_config=read_config,
        run_check=lambda command, directory: 0,
    )
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def completed(cwd: Path) -> Outcome:
    """The outcome of completing the Story, its Task completed before it, no commit named."""
    return runs(cwd, *STARTED, TASK_DONE, STORY_DONE)


def test_complete_of_the_story_without_a_commit_exits_with_zero(tmp_path: Path) -> None:
    assert completed(tmp_path).status == 0


def test_status_lists_the_story_under_completed(tmp_path: Path) -> None:
    completed(tmp_path)
    assert fgraph(["status"], tmp_path).out == (
        "backlog (0)\nin-progress (0)\ncompleted (1)\n  S-0001  a title\n"
    )


def test_complete_of_the_task_without_a_commit_names_the_task_and_its_story_alone(
    tmp_path: Path,
) -> None:
    assert runs(tmp_path, *STARTED, TASK_DONE).out == "completed T-0001 of S-0001\n"


def test_complete_of_the_story_without_a_commit_names_the_story_alone(tmp_path: Path) -> None:
    assert completed(tmp_path).out == "completed S-0001\n"


def test_show_lists_no_commit_of_the_story_nor_of_its_task(tmp_path: Path) -> None:
    completed(tmp_path)
    assert fgraph(["show", "S-0001"], tmp_path).out == (
        "S-0001  a title\n"
        "  bucket       completed\n"
        "  given        a state\n"
        "  when         an action\n"
        "  then         another\n"
        "Tasks (1)\n"
        "  T-0001  a task title\n"
        "    bucket           completed\n"
        "    expected output  an output\n"
    )


def test_a_story_completed_without_a_commit_keeps_the_commit_given_for_its_task(
    tmp_path: Path,
) -> None:
    runs(tmp_path, *STARTED, TASK_DONE_IN_A_COMMIT, STORY_DONE)
    assert fgraph(["show", "S-0001"], tmp_path).out.splitlines()[-3:] == [
        "    bucket           completed",
        "    commit           abc1234",
        "    expected output  an output",
    ]


@pytest.fixture
def developed(tmp_path: Path) -> Path:
    """A record that turns the development on, with a started Story and its started Task."""
    (tmp_path / ".fgraph").mkdir()
    (tmp_path / ".fgraph" / "config.toml").write_text(
        "[development]\nenabled = true\n", encoding="utf-8"
    )
    runs(tmp_path, *STARTED_CHECKED)
    return tmp_path


@pytest.mark.parametrize(
    ("argvs", "named"),
    [([TASK_DONE], "T-0001"), ([TASK_DONE_IN_A_COMMIT, STORY_DONE], "S-0001")],
    ids=["task", "story"],
)
def test_a_complete_without_a_commit_with_the_development_on_exits_with_two_naming_the_key(
    argvs: list[list[str]], named: str, developed: Path
) -> None:
    outcome = runs(developed, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (
        2,
        f"fgraph: error: {named} {NEEDED}",
    )


def test_a_complete_refused_for_its_commit_leaves_the_task_started(developed: Path) -> None:
    runs(developed, TASK_DONE)
    assert fgraph(["status"], developed).out == (
        "backlog (0)\n"
        "in-progress (1)\n"
        "  S-0001  0/1 T  a title\n"
        "    => T-0001  a task title\n"
        "completed (0)\n"
    )
