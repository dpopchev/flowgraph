"""The criterion of removing a Feature: `fgraph status` lists it under Removed with its reason.

Its work items are removed with it, for the same reason, and are on no line of their own. Run
end to end on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_UNDER = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
REMOVE = ["remove", "F-0001", "--reason", "filed by mistake"]
NO_FEATURE_YET = "S-0058: fgraph remove takes no Feature yet"


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


class TestAFeatureInBacklogWithAStoryUnderItRemovedWithAReason:
    @pytest.fixture
    def removed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_FEATURE, ADD_UNDER, REMOVE)

    @pytest.mark.xfail(strict=True, reason=NO_FEATURE_YET)
    def test_remove_exits_with_zero(self, removed: Outcome) -> None:
        assert removed.status == 0

    @pytest.mark.xfail(strict=True, reason=NO_FEATURE_YET)
    def test_status_lists_it_under_removed_with_its_reason(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (0)\n"
            "InProgress (0)\n"
            "Completed (0)\n"
            "Removed (1)\n"
            "  F-0001  a feature title  -- filed by mistake\n"
        )
