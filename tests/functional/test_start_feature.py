"""The criterion of starting a Feature: `fgraph status` lists it under InProgress.

Its first Story is started with it and listed under it. Run end to end on a record in a
temporary directory, through the file adapters of the package, each command one second after the
one before it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0052: fgraph start takes no Feature yet"),
]

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
TWO_STORIES = (ADD_FEATURE, ADD_STORY, ADD_OTHER, ADD_TASK, TASK_FOR_OTHER)


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


class TestAFeatureInBacklogWithTwoStoriesEachWithATaskStarted:
    @pytest.fixture
    def started(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *TWO_STORIES, ["start", "F-0001"])

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_status_lists_the_feature_under_in_progress_with_its_first_story_under_it(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, START + timedelta(minutes=1)).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  F-0001  0/2 W  a feature title\n"
            "    S-0001  0/1 T  a title\n"
            "Completed (0)\n"
        )
