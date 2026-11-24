"""The criterion of a work item that waits: `fgraph status` marks its line in Backlog.

Two Stories in Backlog, the second depending on the first: the line of the second is marked
and names the first, and once the first is completed the line carries no mark. Run end to end
on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FIRST = ["add", "story", "a first title", *CRITERION]
ADD_SECOND = ["add", "story", "a second title", *CRITERION]
TASK_FOR_FIRST = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
TASK_FOR_SECOND = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
DEPEND = ["amend", "S-0002", "--depends-on", "S-0001"]
WAITING = (ADD_FIRST, ADD_SECOND, TASK_FOR_FIRST, TASK_FOR_SECOND, DEPEND)
FIRST_DONE = (
    ["start", "S-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "def5678"],
)
STATUS = ["status", "--backlog"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
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
    )
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def line_of(out: str, item: str) -> str:
    """The line of the status that lists the item, without its newline."""
    return next(line for line in out.splitlines() if f" {item} " in line)


def test_status_of_a_waiting_story_exits_0(tmp_path: Path) -> None:
    assert runs(tmp_path, *WAITING, STATUS).status == 0


def test_line_of_a_waiting_story_is_marked(tmp_path: Path) -> None:
    out = runs(tmp_path, *WAITING, STATUS).out
    assert line_of(out, "S-0002").startswith("~ ")


def test_line_of_a_waiting_story_names_what_it_waits_for(tmp_path: Path) -> None:
    out = runs(tmp_path, *WAITING, STATUS).out
    assert line_of(out, "S-0002").endswith("-- depends on S-0001")


def test_line_of_a_story_whose_dependency_is_completed_carries_no_mark(tmp_path: Path) -> None:
    out = runs(tmp_path, *WAITING, *FIRST_DONE, STATUS).out
    assert line_of(out, "S-0002") == "> S-0002  [1 T]  a second title"
