"""The criterion of a work item that depends on another: its start is refused until that completes.

Two Stories in Backlog, the second amended to depend on the first: `fgraph start` of the second
exits with 2 naming the first and its bucket, and `fgraph show` of the second lists it. Run end
to end on a record in a temporary directory, through the file adapters of the package.
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
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_OTHER = ["add", "story", "another title", *CRITERION]
TASK_FOR_FIRST = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
TASK_FOR_SECOND = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
DEPEND = ["amend", "S-0002", "--depends-on", "S-0001"]
TWO_STORIES = (ADD_STORY, ADD_OTHER, TASK_FOR_FIRST, TASK_FOR_SECOND)


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


def test_amend_with_depends_on_exits_with_zero(tmp_path: Path) -> None:
    assert runs(tmp_path, *TWO_STORIES, DEPEND).status == 0


def test_start_of_the_dependent_exits_with_two(tmp_path: Path) -> None:
    assert runs(tmp_path, *TWO_STORIES, DEPEND, ["start", "S-0002"]).status == 2


def test_start_of_the_dependent_names_what_it_depends_on_and_its_bucket(tmp_path: Path) -> None:
    refused = runs(tmp_path, *TWO_STORIES, DEPEND, ["start", "S-0002"])
    expected = "fgraph: error: S-0002 cannot start: it depends on S-0001, in Backlog"
    assert refused.err.splitlines()[-1] == expected


def test_show_of_the_dependent_lists_that_it_depends_on_the_first(tmp_path: Path) -> None:
    shown = runs(tmp_path, *TWO_STORIES, DEPEND, ["show", "S-0002"]).out
    assert "  depends on   S-0001 (Backlog)\n" in shown
