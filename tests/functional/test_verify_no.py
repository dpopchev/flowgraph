"""The criterion of S-0094: a no of fgraph verify files a Bug that amends the completed Story.

On a record with a completed Story, `fgraph verify S-0001 --no` with what the run printed exits
with 0 and names a new Bug in Backlog that amends the Story, its observed the text; the Story stays
Completed, listed as verified, no. Run end to end on a record in a temporary directory, through
the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from tests.functional.completed_story import STANDING_ALONE

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0094: fgraph verify --no is not offered yet"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TEXT = "status listed no reason"
VERIFY = ["verify", "S-0001", "--no", TEXT]


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


class TestACompletedStoryVerifiedNo:
    @pytest.fixture
    def verified(self, tmp_path: Path) -> Outcome:
        """The outcome of a no on a Story that stands alone, completed."""
        runs(tmp_path, *STANDING_ALONE)
        return fgraph(VERIFY, tmp_path)

    def test_verify_exits_with_zero(self, verified: Outcome) -> None:
        assert verified.status == 0

    def test_verify_prints_the_id_of_the_new_bug(self, verified: Outcome) -> None:
        assert "B-0001" in verified.out

    def test_show_of_the_bug_lists_it_in_backlog(self, verified: Outcome, tmp_path: Path) -> None:
        assert "  bucket       Backlog\n" in fgraph(["show", "B-0001"], tmp_path).out

    def test_show_of_the_bug_lists_the_story_it_amends(
        self, verified: Outcome, tmp_path: Path
    ) -> None:
        assert "  amends       S-0001\n" in fgraph(["show", "B-0001"], tmp_path).out

    def test_show_of_the_bug_lists_the_text_as_its_observed(
        self, verified: Outcome, tmp_path: Path
    ) -> None:
        assert f"  observed     {TEXT}\n" in fgraph(["show", "B-0001"], tmp_path).out

    def test_show_of_the_story_lists_it_completed(self, verified: Outcome, tmp_path: Path) -> None:
        assert "  bucket       Completed\n" in fgraph(["show", "S-0001"], tmp_path).out

    def test_show_of_the_story_lists_it_as_verified_no_with_the_text_and_the_day(
        self, verified: Outcome, tmp_path: Path
    ) -> None:
        shown = fgraph(["show", "S-0001"], tmp_path).out
        assert f"  verified     no  2026-01-01  {TEXT}\n" in shown
