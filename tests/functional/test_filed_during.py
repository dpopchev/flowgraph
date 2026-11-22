"""The criterion of a work item found during another: each shows the other.

On a record with a started Story, `fgraph add bug` with `--filed-during` and the id of the Story
exits with 0; `fgraph show` of the Bug lists the Story it was filed during, and `fgraph show` of
the Story lists the Bug as filed during it. Run end to end on a record in a temporary directory,
through the file adapters of the package.
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
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
STARTED_STORY = (ADD_STORY, ADD_TASK, ["start", "S-0001"])
ADD_BUG = [
    *("add", "bug", "a bug title", "--observed", "it fails", "--expected", "it works"),
    *("--filed-during", "S-0001"),
]


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


def test_add_bug_filed_during_the_story_exits_with_zero(tmp_path: Path) -> None:
    assert runs(tmp_path, *STARTED_STORY, ADD_BUG).status == 0


def test_show_of_the_bug_lists_the_story_it_was_filed_during(tmp_path: Path) -> None:
    shown = runs(tmp_path, *STARTED_STORY, ADD_BUG, ["show", "B-0001"]).out
    assert "  filed during S-0001\n" in shown


def test_show_of_the_story_lists_the_bug_as_filed_during_it(tmp_path: Path) -> None:
    shown = runs(tmp_path, *STARTED_STORY, ADD_BUG, ["show", "S-0001"]).out
    assert "  filed here   B-0001\n" in shown
