"""The criterion of reordering a Feature: `fgraph status` lists it above the Story it precedes.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0051: fgraph reorder takes no Feature yet"),
]

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title that stands alone", *CRITERION]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
REORDER = ["reorder", "F-0001", "--before", "S-0001"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, at: datetime) -> Outcome:
    """Run the command at that time in cwd, whose record is `.fgraph/`, on the files of it."""
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
        now=lambda: at,
    )
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the last; the outcome of the last."""
    outcomes = [
        fgraph(argv, cwd, START + timedelta(seconds=seconds)) for seconds, argv in enumerate(argvs)
    ]
    return outcomes[-1]


class TestAFeaturePutBeforeAStoryAddedBeforeIt:
    @pytest.fixture
    def reordered(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_FEATURE, REORDER)

    def test_reorder_exits_with_zero(self, reordered: Outcome) -> None:
        assert reordered.status == 0

    def test_status_lists_the_feature_before_the_story(
        self, reordered: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, START + timedelta(minutes=1)).out == (
            "Backlog (2)\n"
            "  F-0001  0/0 W  a feature title\n"
            "  S-0001  a title that stands alone\n"
            "InProgress (0)\n"
            "Completed (0)\n"
        )
