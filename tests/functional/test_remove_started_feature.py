"""The criterion of S-0125: a started or blocked Feature is removed with no work item started.

`fgraph remove` takes it to Removed with its reason; its completed work item stays Completed under
it, and one in Backlog is removed with it. Run end to end on a record in a temporary directory,
through the file adapters of the package, with the development off.
"""

import json
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
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
BLOCK = ["block", "F-0001", "--reason", "a reason", "--waiting-on", "the sponsor"]
COMPLETE = [
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "abc1234"],
]
REMOVE = ["remove", "F-0001", "--reason", "pivoted"]
REMOVE_OTHER = ["remove", "S-0002", "--reason", "superseded"]
# Two Stories, the first with a Task; the second has none, so no completion starts it.
FILED = (ADD_FEATURE, ADD_UNDER, ADD_TASK, ADD_OTHER, ["start", "F-0001"])
# The first Story completed, the second left in Backlog: a blocked Feature starts none.
BLOCKED_DONE = (*FILED, BLOCK, *COMPLETE)
STARTED_DONE = (*FILED, *COMPLETE)
BLOCKED_APART = (*BLOCKED_DONE, REMOVE_OTHER)
STARTED_APART = (*STARTED_DONE, REMOVE_OTHER)
GONE = "F-0001 is removed already"
HELD = "F-0001 cannot be removed: S-0001 is started already"

red = pytest.mark.xfail(
    strict=True, reason="S-0125: a started or blocked Feature is not removed yet"
)


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


class TestABlockedFeatureTakenApartRemovedWithAReason:
    @pytest.fixture
    def removed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *BLOCKED_APART, REMOVE)

    @red
    def test_remove_exits_with_zero(self, removed: Outcome) -> None:
        assert removed.status == 0

    @red
    def test_remove_names_the_feature(self, removed: Outcome) -> None:
        assert removed.out == "removed F-0001\n"

    @red
    def test_status_lists_it_alone_under_removed_with_its_reason(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (0)\n"
            "InProgress (0)\n"
            "Completed (0)\n"
            "Removed (1)\n"
            "  F-0001  a feature title  -- pivoted\n"
        )

    @red
    def test_show_of_it_lists_its_reason_and_its_two_work_items(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "F-0001"], tmp_path).out == (
            "F-0001  a feature title\n"
            "  bucket       Removed\n"
            "  reason       pivoted\n"
            "Criteria (1)\n"
            "  a criterion\n"
            "Work items (2)\n"
            "  S-0001  a title  Completed\n"
            "  S-0002  another title  Removed\n"
        )

    @red
    def test_status_json_lists_it_under_removed_with_its_progress_and_work_items(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        document = json.loads(fgraph(["status", "--format", "json"], tmp_path).out)
        bucket = next(b for b in document["buckets"] if b["name"] == "Removed")
        assert [
            (
                item["id"],
                item["reason"],
                (item["progress"]["completed"], item["progress"]["total"]),
                [(w["id"], w["state"]) for w in item["work_items"]],
            )
            for item in bucket["items"]
        ] == [("F-0001", "pivoted", (1, 1), [("S-0001", "completed"), ("S-0002", "removed")])]

    def test_its_completed_story_keeps_its_bucket_and_its_parent(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], tmp_path).out.splitlines()[1:3] == [
            "  bucket       Completed",
            "  parent       F-0001",
        ]

    def test_its_story_removed_before_keeps_the_reason_it_had(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert "  reason       superseded" in fgraph(["show", "S-0002"], tmp_path).out


@red
def test_a_started_feature_taken_apart_is_removed(tmp_path: Path) -> None:
    removed = runs(tmp_path, *STARTED_APART, REMOVE)
    assert (removed.status, removed.out) == (0, "removed F-0001\n")


class TestABlockedFeatureRemovedWithItsStoryInBacklog:
    @pytest.fixture
    def removed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *BLOCKED_DONE, REMOVE)

    @red
    def test_remove_exits_with_zero(self, removed: Outcome) -> None:
        assert removed.status == 0

    @red
    def test_its_story_in_backlog_is_removed_for_the_reason_of_the_feature(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0002"], tmp_path).out.splitlines()[1:4] == [
            "  bucket       Removed",
            "  parent       F-0001",
            "  reason       pivoted",
        ]


STARTED_HOLDING = (*FILED, REMOVE)
BLOCKED_HOLDING = (*FILED, BLOCK, REMOVE)


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        pytest.param(STARTED_HOLDING, HELD, marks=red, id="a-started-feature-holding-a-story"),
        pytest.param(BLOCKED_HOLDING, HELD, marks=red, id="a-blocked-feature-holding-a-story"),
        pytest.param((*BLOCKED_APART, REMOVE, REMOVE), GONE, marks=red, id="removed-twice"),
        pytest.param(
            (*BLOCKED_APART, ["remove", "F-0001", "--reason", " "]),
            "reason is empty",
            marks=red,
            id="blank-reason",
        ),
        pytest.param(
            (*BLOCKED_APART, [*REMOVE, "--superseded-by", "S-0001"]),
            "F-0001 is a Feature: it is removed with --reason alone",
            id="superseded-by-given",
        ),
    ],
)
def test_a_remove_refused_exits_with_two_and_names_why(
    argvs: tuple[Sequence[str], ...], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])


@pytest.mark.parametrize(
    ("move", "error"),
    [
        pytest.param(["complete", "F-0001"], GONE, marks=red, id="complete"),
        pytest.param(ADD_UNDER, GONE, marks=red, id="add-under"),
        pytest.param(["unblock", "F-0001"], "F-0001 is not blocked", marks=red, id="unblock"),
    ],
)
def test_a_move_of_a_feature_removed_from_in_progress_exits_with_two(
    move: Sequence[str], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *BLOCKED_APART, REMOVE, move)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])


def test_a_remove_refused_for_a_started_story_leaves_the_status_as_it_was(tmp_path: Path) -> None:
    before = runs(tmp_path, *STARTED_HOLDING[:-1], ["status"]).out
    assert runs(tmp_path, REMOVE, ["status"]).out == before
