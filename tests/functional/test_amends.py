"""The criterion of a work item that amends a completed one: each shows the other.

On a record with a completed Story, `fgraph add story` with `--amends` and the id of the completed
Story exits with 0; `fgraph show` of the new Story lists the Story it amends, and `fgraph show`
of the completed Story lists the new one as amending it. Run end to end on a record in a
temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from tests.functional.completed_story import ADD_STORY
from tests.functional.completed_story import STANDING_ALONE as COMPLETED_STORY

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
AMEND = [*ADD_STORY, "--amends", "S-0001"]


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


def test_add_story_amending_the_completed_story_exits_with_zero(tmp_path: Path) -> None:
    assert runs(tmp_path, *COMPLETED_STORY, AMEND).status == 0


def test_show_of_the_new_story_lists_the_story_it_amends(tmp_path: Path) -> None:
    shown = runs(tmp_path, *COMPLETED_STORY, AMEND, ["show", "S-0002"]).out
    assert "  amends       S-0001\n" in shown


def test_show_of_the_completed_story_lists_the_new_one_as_amending_it(tmp_path: Path) -> None:
    shown = runs(tmp_path, *COMPLETED_STORY, AMEND, ["show", "S-0001"]).out
    assert "  amended by   S-0002\n" in shown
