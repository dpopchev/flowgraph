"""The criterion of S-0162: fgraph brief lists under Governed by the live lines alone.

Run end to end through `run` on a record in a temporary directory, through the file adapters of
the package; no git is opened, so a --governs path is kept as given.
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
STORY = ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]
TASK = [
    "add",
    "task",
    "a task title",
    "--parent",
    "S-0001",
    "--output",
    "changed: src/gate.py holds the gate",
]
OLD = "the gate holds a state"
NEW = "the gate holds no state"
FIRST = ["note", "S-0001", "--decision", OLD, "--governs", "src/gate.py"]
SUPERSEDING = [
    "note",
    "S-0001",
    "--decision",
    NEW,
    "--governs",
    "src/gate.py",
    "--supersedes",
    "S-0001#1",
]
BESIDE = ["note", "S-0001", "--decision", NEW, "--governs", "src/gate.py"]
BRIEF = ["brief", "S-0001"]
BRIEF_JSON = ["brief", "S-0001", "--format", "json"]
SHOW = ["show", "S-0001"]


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
    try:
        status = run(
            argv,
            cwd,
            Path.is_dir,
            out.append,
            err.append,
            open_store=open_files,
            now=lambda: NOW,
            open_git=lambda _: None,
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def governed_texts(cwd: Path) -> list[str]:
    """The text of each line the JSON brief of S-0001 lists under governed_by."""
    document = json.loads(runs(cwd, BRIEF_JSON).out)
    return [line["text"] for line in document["governed_by"]]


def test_the_brief_lists_the_live_line_alone_under_governed_by(tmp_path: Path) -> None:
    out = runs(tmp_path, STORY, TASK, FIRST, SUPERSEDING, BRIEF).out
    governed = out.partition("Governed by\n")[2]
    assert governed == f"  decision  2026-01-01  S-0001  {NEW}\n"


def test_the_brief_as_json_holds_the_live_line_alone(tmp_path: Path) -> None:
    runs(tmp_path, STORY, TASK, FIRST, SUPERSEDING)
    assert governed_texts(tmp_path) == [NEW]


def test_with_no_supersede_the_brief_lists_both_lines(tmp_path: Path) -> None:
    runs(tmp_path, STORY, TASK, FIRST, BESIDE)
    assert sorted(governed_texts(tmp_path)) == sorted([OLD, NEW])


def test_show_keeps_the_superseded_line_with_its_superseded_by_mark(tmp_path: Path) -> None:
    runs(tmp_path, STORY, TASK, FIRST, SUPERSEDING)
    assert "superseded by S-0001#2" in runs(tmp_path, SHOW).out
