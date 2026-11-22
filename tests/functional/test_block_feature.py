"""The criterion of blocking a Feature: `fgraph status` lists it under InProgress with `!`.

The line of a started Feature blocked with a reason and what it waits on starts with `!` and
ends with what it waits on. Run end to end on a record in a temporary directory, through the
file adapters of the package, each command one second after the one before it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
LATER = START + timedelta(minutes=1)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
BLOCK = ["block", "F-0001", "--reason", "the budget is not agreed", "--waiting-on", "the sponsor"]
STARTED = (ADD_FEATURE, ADD_STORY, ADD_TASK, ["start", "F-0001"])
NOT_BLOCKED_YET = "S-0056: fgraph block takes no Feature yet"


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


class TestAStartedFeatureBlockedWithAReasonAndWhatItWaitsOn:
    @pytest.fixture
    def blocked(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *STARTED, BLOCK)

    @pytest.mark.xfail(strict=True, reason=NOT_BLOCKED_YET)
    def test_block_exits_with_zero(self, blocked: Outcome) -> None:
        assert blocked.status == 0

    @pytest.mark.xfail(strict=True, reason=NOT_BLOCKED_YET)
    def test_status_lists_it_under_inprogress_with_the_mark_and_what_it_waits_on(
        self, blocked: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "! F-0001  0/1 W  a feature title  -- waiting on the sponsor\n"
            "    S-0001  0/1 T  a title\n"
            "Completed (0)\n"
        )
