"""The criterion of S-0163: fgraph brief lists the terms its governing lines are about.

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
MEANING = "a check every deliverable passes before it lands"
GATE = ["add", "term", "gate", "--means", MEANING]
LEASE = ["add", "term", "lease", "--means", "a hold with an end"]
STORY = ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]
ABOUT = [*STORY, "--about", "gate"]
TASK = [
    "add",
    "task",
    "a task title",
    "--parent",
    "S-0001",
    "--output",
    "changed: src/gate.py holds the gate",
]
OTHER = ["add", "story", "another title", "--given", "a", "--when", "b", "--then", "c"]
GOVERNING = [
    "note",
    "S-0002",
    "--decision",
    "the gate holds no state",
    "--governs",
    "src/gate.py",
    "--about",
    "gate",
]
ELSEWHERE = [
    "note",
    "S-0002",
    "--finding",
    "the lease ends",
    "--governs",
    "src/lease.py",
    "--about",
    "lease",
]
XFAIL = pytest.mark.xfail(
    strict=True, reason="S-0163: the brief lists no term a governing line is about"
)
GATE_LINE = f"  gate  {MEANING}"


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


def brief_of(cwd: Path, item: str) -> Outcome:
    """The brief of the work item in cwd, as text."""
    return fgraph(["brief", item], cwd)


@XFAIL
def test_the_brief_lists_the_term_a_governing_line_is_about(tmp_path: Path) -> None:
    """A term a line under Governed by is about is listed under Terms with its meaning."""
    runs(tmp_path, GATE, LEASE, STORY, TASK, OTHER, GOVERNING, ELSEWHERE)
    out = brief_of(tmp_path, "S-0001").out
    assert out.endswith(f"Terms (1)\n{GATE_LINE}\n")


@XFAIL
def test_the_brief_as_json_holds_the_term(tmp_path: Path) -> None:
    """The JSON brief lists the term a governing line is about, with its meaning."""
    runs(tmp_path, GATE, LEASE, STORY, TASK, OTHER, GOVERNING, ELSEWHERE)
    out = fgraph(["brief", "S-0001", "--format", "json"], tmp_path).out
    assert json.loads(out)["terms"] == [{"name": "gate", "meaning": MEANING}]


def test_the_term_of_a_line_that_governs_another_file_is_not_listed(tmp_path: Path) -> None:
    """A term a line about another file is about is not listed."""
    runs(tmp_path, GATE, LEASE, STORY, TASK, OTHER, GOVERNING, ELSEWHERE)
    assert "  lease  " not in brief_of(tmp_path, "S-0001").out


def test_a_term_both_about_is_listed_once(tmp_path: Path) -> None:
    """A term the work item and a governing line are both about is listed once."""
    runs(tmp_path, GATE, ABOUT, TASK, OTHER, GOVERNING)
    assert brief_of(tmp_path, "S-0001").out.count(GATE_LINE) == 1
