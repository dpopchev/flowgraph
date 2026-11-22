"""The criterion of a work item removed as superseded: each shows the other.

On a record with two Stories in Backlog, `fgraph remove` of the first with `--superseded-by` and
the id of the second exits with 0; `fgraph status` lists the first under Removed as superseded by
the second, and `fgraph show` of the second lists that it supersedes the first. Run end to end on
a record in a temporary directory, through the file adapters of the package.
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
SUPERSEDE = ["remove", "S-0001", "--superseded-by", "S-0002"]


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


def test_remove_superseded_by_the_second_exits_with_zero(tmp_path: Path) -> None:
    assert runs(tmp_path, ADD_STORY, ADD_OTHER, SUPERSEDE).status == 0


def test_status_lists_the_first_under_removed_as_superseded_by_the_second(tmp_path: Path) -> None:
    listed = runs(tmp_path, ADD_STORY, ADD_OTHER, SUPERSEDE, ["status"]).out
    assert "Removed (1)\n  S-0001  a title  -- superseded by S-0002\n" in listed


def test_show_of_the_second_lists_that_it_supersedes_the_first(tmp_path: Path) -> None:
    shown = runs(tmp_path, ADD_STORY, ADD_OTHER, SUPERSEDE, ["show", "S-0002"]).out
    assert "  supersedes   S-0001\n" in shown
