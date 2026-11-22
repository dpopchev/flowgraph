"""The criterion of S-0064: a decision noted on a Feature is listed under Knowledge by show.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer notes a Feature"]
NOTE = ["note", "F-0001", "--decision", "keep one store"]


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


def test_a_decision_noted_on_a_feature_exits_with_zero(tmp_path: Path) -> None:
    fgraph(ADD_FEATURE, tmp_path)
    assert fgraph(NOTE, tmp_path).status == 0


def test_a_decision_noted_on_a_feature_is_listed_under_knowledge_by_show(tmp_path: Path) -> None:
    fgraph(ADD_FEATURE, tmp_path)
    fgraph(NOTE, tmp_path)
    assert fgraph(["show", "F-0001"], tmp_path).out.endswith(
        "Work items (0)\nKnowledge (1)\n  decision  2026-01-01  keep one store\n"
    )
