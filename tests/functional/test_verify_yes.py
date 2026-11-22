"""The criterion of S-0093: fgraph verify keeps the yes of the closing of a completed Story.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from tests.functional.completed_story import ADD_STORY, ADD_TASK, STANDING_ALONE

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0093: fgraph verify is not added yet"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TEXT = "make check: all checks passed"
VERIFY = ["verify", "S-0001", "--yes", TEXT]
STORY_FILE = Path(".fgraph") / "items" / "S-0001.toml"


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


class TestACompletedStoryVerified:
    @pytest.fixture
    def verified(self, tmp_path: Path) -> Outcome:
        """The outcome of the verify of a Story that stands alone, completed."""
        runs(tmp_path, *STANDING_ALONE)
        return fgraph(VERIFY, tmp_path)

    def test_verify_exits_with_zero(self, verified: Outcome) -> None:
        assert verified.status == 0

    def test_show_lists_it_as_verified_yes_with_the_text_and_the_day(
        self, verified: Outcome, tmp_path: Path
    ) -> None:
        shown = fgraph(["show", "S-0001"], tmp_path).out
        assert f"  verified     yes  2026-01-01  {TEXT}\n" in shown


class TestAStoryNotCompletedVerified:
    @pytest.fixture
    def refused(self, tmp_path: Path) -> Outcome:
        """The outcome of the verify of a Story in Backlog."""
        runs(tmp_path, ADD_STORY, ADD_TASK)
        return fgraph(VERIFY, tmp_path)

    def test_verify_exits_with_two(self, refused: Outcome) -> None:
        assert refused.status == 2

    def test_verify_writes_nothing(self, refused: Outcome, tmp_path: Path) -> None:
        assert "verified" not in (tmp_path / STORY_FILE).read_text(encoding="utf-8")
