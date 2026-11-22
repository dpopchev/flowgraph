"""The criterion of S-0071: two terms related with part-of are shown, each side by its name.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(reason="S-0071: fgraph relate is not there yet", strict=True),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)


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


class TestTwoTermsRelatedWithPartOf:
    @pytest.fixture
    def related(self, tmp_path: Path) -> Outcome:
        fgraph(["add", "term", "gate", "--means", "a check before a landing"], tmp_path)
        fgraph(["add", "term", "lane", "--means", "one work item in its own worktree"], tmp_path)
        return fgraph(["relate", "gate", "part-of", "lane"], tmp_path)

    def test_relate_exits_with_zero(self, related: Outcome) -> None:
        assert related.status == 0

    def test_show_of_the_first_lists_that_it_is_part_of_the_second(
        self, related: Outcome, tmp_path: Path
    ) -> None:
        assert "  part of  lane\n" in fgraph(["show", "gate"], tmp_path).out

    def test_show_of_the_second_lists_the_first_as_its_part(
        self, related: Outcome, tmp_path: Path
    ) -> None:
        assert "  parts  gate\n" in fgraph(["show", "lane"], tmp_path).out
