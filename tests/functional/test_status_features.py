"""The criterion of the Features in status: `fgraph status` lists each in its derived bucket.

Run end to end on a record in a temporary directory, through the file adapters of the package.
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
ADD_OTHER_FEATURE = ["add", "feature", "another feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_ALONE = ["add", "story", "a title that stands alone", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]


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


def status_after(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn, then `fgraph status`; the outcome of the status."""
    for argv in argvs:
        fgraph(argv, cwd)
    return fgraph(["status"], cwd)


class TestARecordWithAFeatureAndAStoryAddedUnderIt:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return status_after(tmp_path, ADD_FEATURE, ADD_STORY, ADD_ALONE)

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_status_lists_the_feature_in_its_derived_bucket_in_place_of_its_story(
        self, listed: Outcome
    ) -> None:
        assert listed.out == (
            "Backlog (2)\n"
            "  S-0002  a title that stands alone\n"
            "  F-0001  0/1 W  a feature title\n"
            "InProgress (0)\n"
            "Completed (0)\n"
        )


def test_a_feature_with_a_started_story_is_listed_in_progress_with_the_story_under_it(
    tmp_path: Path,
) -> None:
    listed = status_after(tmp_path, ADD_FEATURE, ADD_STORY, ADD_TASK, ["start", "F-0001"])
    assert listed.out.splitlines()[1:4] == [
        "InProgress (1)",
        "  F-0001  0/1 W  a feature title",
        "    S-0001  0/1 T  a title",
    ]


def test_a_feature_whose_story_is_completed_is_listed_completed_with_the_commit_of_the_story(
    tmp_path: Path,
) -> None:
    listed = status_after(
        tmp_path,
        ADD_FEATURE,
        ADD_STORY,
        ADD_TASK,
        ["start", "F-0001"],
        ["start", "T-0001"],
        ["complete", "T-0001", "--commit", "abc1234"],
        ["complete", "S-0001", "--commit", "def5678"],
    )
    assert listed.out.splitlines()[2:] == [
        "Completed (1)",
        "  F-0001  1/1 W  def5678  a feature title",
    ]


def test_the_features_added_at_one_time_are_listed_by_number(tmp_path: Path) -> None:
    listed = status_after(tmp_path, ADD_FEATURE, ADD_OTHER_FEATURE, ADD_STORY)
    assert listed.out.splitlines()[:3] == [
        "Backlog (2)",
        "  F-0001  0/1 W  a feature title",
        "  F-0002  0/0 W  another feature title",
    ]


def test_a_record_with_a_feature_lists_no_heading_for_the_features(tmp_path: Path) -> None:
    assert status_after(tmp_path, ADD_FEATURE).out.splitlines()[0] == "Backlog (1)"
