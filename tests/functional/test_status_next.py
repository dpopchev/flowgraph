"""The criterion of the next to start: `fgraph status` names the first item that can start.

A Backlog whose first item waits and whose second waits for nothing: can_start of the JSON
names the second, and no line is marked. When the top of the heading leaves it out it is counted
in the more-line.
Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

import json
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
DEPEND = ["amend", "S-0001", "--depends-on", "S-0002"]
FIRST_WAITS = (ADD_FIRST, ADD_SECOND, DEPEND)
SEVEN = [
    *(["add", "story", f"title {number}", *CRITERION] for number in range(1, 8)),
    *(["amend", f"S-000{number}", "--depends-on", "S-0007"] for number in range(1, 7)),
]
ALL_WAIT = (
    ADD_FIRST,
    ADD_SECOND,
    ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"],
    ["start", "S-0001"],
    ["amend", "S-0002", "--depends-on", "S-0001"],
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


def can_start(cwd: Path, *argvs: Sequence[str]) -> list[str]:
    """The ids the JSON of status lists as able to start, after each command in cwd in turn."""
    runs(cwd, *argvs)
    return json.loads(runs(cwd, ["status", "--format", "json"]).out)["can_start"]


def test_status_of_a_backlog_whose_first_item_waits_exits_0(tmp_path: Path) -> None:
    assert runs(tmp_path, *FIRST_WAITS, STATUS).status == 0


def test_status_names_the_second_item_as_the_next_to_start(tmp_path: Path) -> None:
    assert can_start(tmp_path, *FIRST_WAITS) == ["S-0002"]


def test_status_counts_the_next_to_start_in_the_more_line_when_the_top_leaves_it_out(
    tmp_path: Path,
) -> None:
    out = runs(tmp_path, *SEVEN, ["status"]).out
    assert out.splitlines()[3] == "  ... 6 more, 1 can start"


def test_status_names_none_when_no_item_of_the_backlog_can_start(tmp_path: Path) -> None:
    assert can_start(tmp_path, *ALL_WAIT) == []
