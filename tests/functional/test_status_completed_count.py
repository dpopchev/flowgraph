"""The criterion of S-0134: `fgraph status` lists a completed item with no count of what it holds.

A completed Feature is listed with its id, its commit and its title, a completed Story standing
alone with its id, its commit and its title; neither with a count of its work items. Run end to
end on a record in a temporary directory, through the file adapters of the package, each command
one second after the one before it.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from tests.functional.completed_story import COMPLETIONS

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
LATER = START + timedelta(minutes=1)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
TWO_STORIES = (ADD_FEATURE, ADD_STORY, ADD_OTHER, ADD_TASK, TASK_FOR_OTHER)
FIRST_COMPLETED = (["start", "F-0001"], *COMPLETIONS)
# The completion of the first Story starts the second.
SECOND_READY = (
    ["start", "T-0002"],
    ["complete", "T-0002", "--commit", "1234abc"],
)
SECOND_AWAITED = (*TWO_STORIES, *FIRST_COMPLETED, *SECOND_READY)
COMPLETE_SECOND = ["complete", "S-0002", "--commit", "5678def"]
# A Story standing alone, completed before the Feature, so that the Feature is the last completed.
ADD_ALONE = ["add", "story", "title 3", *CRITERION]
ADD_ALONE_TASK = ["add", "task", "a task title", "--parent", "S-0003", "--output", "an output"]
STANDING_ALONE = (
    ADD_ALONE,
    ADD_ALONE_TASK,
    ["start", "S-0003"],
    ["start", "T-0003"],
    ["complete", "T-0003", "--commit", "9abcdef"],
    ["complete", "S-0003", "--commit", "abc1233"],
)
DONE = (*SECOND_AWAITED, *STANDING_ALONE, COMPLETE_SECOND)
ONE_DONE = SECOND_AWAITED
ADDED = (ADD_FEATURE, ADD_STORY)
COMPLETED_LINES = [
    "completed (2)",
    "  F-0001  5678def  a feature title",
    "  S-0003  abc1233  title 3",
]


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


def runs(cwd: Path, *argvs: Sequence[str]) -> None:
    """Run each command in cwd a second after the last."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))


def completed_lines(text: str) -> list[str]:
    """The lines of status from `Completed (N)` on."""
    lines = text.splitlines()
    return lines[lines.index(next(line for line in lines if line.startswith("completed ("))) :]


class TestAFeatureAndAStoryCompletedAreListedWithNoCount:
    def test_status_lists_the_completed_items_with_their_commits_and_no_count(
        self, tmp_path: Path
    ) -> None:
        runs(tmp_path, *DONE)
        assert completed_lines(fgraph(["status"], tmp_path, LATER).out) == COMPLETED_LINES

    def test_no_line_under_completed_holds_a_count_of_work_items_or_tasks(
        self, tmp_path: Path
    ) -> None:
        runs(tmp_path, *DONE)
        listed = completed_lines(fgraph(["status"], tmp_path, LATER).out)[1:]
        assert not any(" W  " in line or " T  " in line for line in listed)

    def test_watch_lists_the_completed_items_as_status_does(self, tmp_path: Path) -> None:
        runs(tmp_path, *DONE)
        assert completed_lines(fgraph(["watch", "--count", "1"], tmp_path, LATER).out) == (
            COMPLETED_LINES
        )

    def test_status_as_json_keeps_the_progress_of_the_completed_feature(
        self, tmp_path: Path
    ) -> None:
        runs(tmp_path, *DONE)
        document = json.loads(fgraph(["status", "--format", "json"], tmp_path, LATER).out)
        feature = next(
            each for b in document["buckets"] for each in b["items"] if each["id"] == "F-0001"
        )
        assert feature["progress"] == {"completed": 2, "total": 2}


class TestAFeatureInProgressKeepsItsCount:
    def test_status_lists_the_feature_under_in_progress_with_its_count(
        self, tmp_path: Path
    ) -> None:
        runs(tmp_path, *ONE_DONE)
        assert "  F-0001  1/2 W  a feature title" in fgraph(["status"], tmp_path, LATER).out

    def test_status_lists_the_feature_in_backlog_with_its_count(self, tmp_path: Path) -> None:
        runs(tmp_path, *ADDED)
        assert "= F-0001  0/1 W  a feature title" in fgraph(["status"], tmp_path, LATER).out
