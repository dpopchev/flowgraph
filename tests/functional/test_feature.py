"""The criterion of a Feature: `fgraph show` lists its work items with their buckets.

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
ADD_FEATURE = [
    *("add", "feature", "a feature title"),
    *("--criterion", "a developer sees every work item by bucket"),
    *("--criterion", "a developer adds every kind of work"),
]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_ALONE = ["add", "story", "a title that stands alone", *CRITERION]
ADD_BUG = [
    *("add", "bug", "a bug title", "--observed", "a traceback", "--expected", "exit 2"),
    *("--parent", "F-0001"),
]
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


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


class TestAFeatureWithAStoryAddedUnderIt:
    @pytest.fixture
    def shown(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_FEATURE, ADD_STORY, ADD_ALONE, ["show", "F-0001"])

    def test_show_exits_with_zero(self, shown: Outcome) -> None:
        assert shown.status == 0

    def test_show_lists_the_story_with_its_bucket_under_the_criteria_of_the_feature(
        self, shown: Outcome
    ) -> None:
        assert shown.out == (
            "F-0001  a feature title\n"
            "  bucket       Backlog\n"
            "Criteria (2)\n"
            "  a developer sees every work item by bucket\n"
            "  a developer adds every kind of work\n"
            "Work items (1)\n"
            "  S-0001  a title  Backlog\n"
        )


def test_a_feature_added_is_named_by_its_id(tmp_path: Path) -> None:
    outcome = fgraph(ADD_FEATURE, tmp_path)
    assert (outcome.status, outcome.out) == (0, "added F-0001\n")


def test_a_story_under_a_feature_names_its_parent(tmp_path: Path) -> None:
    runs(tmp_path, ADD_FEATURE, ADD_STORY)
    assert fgraph(["show", "S-0001"], tmp_path).out.splitlines()[:3] == [
        "S-0001  a title",
        "  bucket       Backlog",
        "  parent       F-0001",
    ]


def test_a_feature_is_in_progress_once_a_work_item_of_it_is_started(tmp_path: Path) -> None:
    runs(tmp_path, ADD_FEATURE, ADD_STORY, ADD_BUG, ADD_TASK, ["start", "F-0001"])
    assert fgraph(["show", "F-0001"], tmp_path).out.splitlines()[1:2] + fgraph(
        ["show", "F-0001"], tmp_path
    ).out.splitlines()[-3:] == [
        "  bucket       InProgress",
        "Work items (2)",
        "  S-0001  a title  InProgress",
        "  B-0001  a bug title  Backlog",
    ]


def test_a_feature_is_completed_once_each_work_item_of_it_is_completed_or_removed(
    tmp_path: Path,
) -> None:
    runs(
        tmp_path,
        ADD_FEATURE,
        ADD_STORY,
        ADD_BUG,
        ADD_TASK,
        ["start", "F-0001"],
        ["start", "T-0001"],
        ["complete", "T-0001", "--commit", "abc1234"],
        ["complete", "S-0001", "--commit", "def5678"],
        ["remove", "B-0001", "--reason", "not a bug"],
    )
    assert fgraph(["show", "F-0001"], tmp_path).out.splitlines()[1] == "  bucket       Completed"


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([["add", "feature", "a feature title", "--criterion", " "]], "criterion is empty"),
        ([["add", "feature", " ", "--criterion", "a criterion"]], "title is empty"),
        ([ADD_STORY], "no Feature F-0001 in the record"),
        (
            [ADD_FEATURE, [*ADD_ALONE, "--parent", "S-0001"]],
            "'S-0001' is no Feature id: it is F- and a number",
        ),
        ([["show", "F-0001"]], "no Feature F-0001 in the record"),
    ],
    ids=["blank-criterion", "blank-title", "no-such-feature", "a-story-as-parent", "show-none"],
)
def test_a_feature_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])
