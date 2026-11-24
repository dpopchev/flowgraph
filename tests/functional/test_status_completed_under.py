"""The criterion of S-0133: `fgraph status` lists a completed work item under its Feature.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it.
"""

import json
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
ADD_FIRST = ["add", "story", "title 1", *CRITERION, "--parent", "F-0001"]
ADD_SECOND = ["add", "story", "title 2", *CRITERION, "--parent", "F-0001"]
ADD_FIRST_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_SECOND_TASK = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
ONE_DONE = [
    ADD_FEATURE,
    ADD_FIRST,
    ADD_SECOND,
    ADD_FIRST_TASK,
    ADD_SECOND_TASK,
    ["start", "F-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1231"],
    ["complete", "S-0001", "--commit", "abc1231"],
    ["start", "T-0002"],
]
BOTH_DONE = [
    *ONE_DONE,
    ["complete", "T-0002", "--commit", "abc1232"],
    ["complete", "S-0002", "--commit", "abc1232"],
]
LISTED_UNDER = [
    "InProgress (1)",
    "  F-0001  1/2 W  a feature title",
    "    S-0002  0/1 T  title 2",
    "      => T-0002  a task title",
    "    S-0001  1/1 T  title 1",
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
        run_check=lambda command, directory: 0,
    )
    return Outcome(status, "".join(out), "".join(err))


def status_after(cwd: Path, argvs: Sequence[Sequence[str]], last: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the one before, then the last; its outcome."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(last, cwd, START + timedelta(seconds=len(argvs)))


def in_progress(lines: list[str]) -> list[str]:
    """The lines of status from `InProgress (1)` up to and without `Completed (0)`."""
    return lines[lines.index("InProgress (1)") : lines.index("Completed (0)")]


class TestAFeatureInProgressWithItsFirstWorkItemCompleted:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> list[str]:
        return status_after(tmp_path, ONE_DONE, ["status"]).out.splitlines()

    def test_the_completed_work_item_is_listed_after_the_started_one(
        self, listed: list[str]
    ) -> None:
        assert in_progress(listed) == LISTED_UNDER

    def test_the_completed_work_item_is_the_last_line_under_the_feature(
        self, listed: list[str]
    ) -> None:
        assert listed[-2] == "    S-0001  1/1 T  title 1"

    def test_watch_lists_under_the_feature_the_same_lines_as_status(
        self, tmp_path: Path, listed: list[str]
    ) -> None:
        watched = fgraph(["watch", "--count", "1"], tmp_path, START + timedelta(seconds=99))
        assert in_progress(watched.out.splitlines()) == LISTED_UNDER

    def test_the_completed_work_item_is_on_no_line_of_completed(self, listed: list[str]) -> None:
        assert "Completed (0)" in listed

    def test_status_as_json_lists_both_work_items_under_the_feature(self, tmp_path: Path) -> None:
        status_after(tmp_path, ONE_DONE, ["status"])
        document = json.loads(fgraph(["status", "--format", "json"], tmp_path, START).out)
        feature = next(
            each for b in document["buckets"] for each in b["items"] if each["id"] == "F-0001"
        )
        assert len(feature["work_items"]) == 2


class TestAFeatureCompletedOfItsTwoWorkItems:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> list[str]:
        return status_after(tmp_path, BOTH_DONE, ["status"]).out.splitlines()

    def test_no_line_names_the_first_work_item(self, listed: list[str]) -> None:
        assert not any("S-0001" in line for line in listed)

    def test_no_line_names_the_second_work_item(self, listed: list[str]) -> None:
        assert not any("S-0002" in line for line in listed)
