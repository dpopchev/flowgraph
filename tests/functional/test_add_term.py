"""The criterion of S-0070: a term added with its meaning is listed and shown by its name.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOT_YET = pytest.mark.xfail(strict=True, reason="S-0070: fgraph has no terms yet")

NOW = datetime(2026, 1, 1, tzinfo=UTC)
MEANING = "a check every deliverable passes before it lands"


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path) -> Outcome:
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


class TestATermAddedToARecordWithNoTerms:
    @pytest.fixture
    def added(self, tmp_path: Path) -> Outcome:
        return fgraph(["add", "term", "gate", "--means", MEANING], tmp_path)

    @NOT_YET
    def test_add_exits_with_zero(self, added: Outcome) -> None:
        assert added.status == 0

    @NOT_YET
    def test_terms_lists_it_with_its_meaning(self, added: Outcome, tmp_path: Path) -> None:
        assert fgraph(["terms"], tmp_path).out == f"gate  {MEANING}\n"

    @NOT_YET
    def test_show_of_its_name_prints_its_meaning(self, added: Outcome, tmp_path: Path) -> None:
        assert MEANING in fgraph(["show", "gate"], tmp_path).out
