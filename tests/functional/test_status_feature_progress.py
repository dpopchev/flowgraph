"""The criterion of the progress of a Feature: `fgraph status` lists its work items completed.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
COMPLETE_FIRST = [
    ["start", "F-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "abc1234"],
]
ONE_OF_TWO = [ADD_FEATURE, ADD_STORY, ADD_OTHER, ADD_TASK, *COMPLETE_FIRST]


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


def status_after(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the last, then `fgraph status`; its outcome."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(["status"], cwd, START + timedelta(seconds=len(argvs)))


class TestAFeatureWithOneOfItsTwoStoriesCompleted:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return status_after(tmp_path, *ONE_OF_TWO)

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_status_lists_the_feature_with_its_work_items_completed_of_all(
        self, listed: Outcome
    ) -> None:
        assert listed.out == (
            "Backlog (0)\nInProgress (1)\n  F-0001  1/2 W  a feature title\nCompleted (0)\n"
        )


def test_a_removed_story_is_counted_in_neither_number(tmp_path: Path) -> None:
    listed = status_after(tmp_path, *ONE_OF_TWO, ["remove", "S-0002", "--reason", "a reason"])
    assert listed.out.splitlines()[1:3] == ["InProgress (1)", "  F-0001  1/1 W  a feature title"]
