"""The criterion of removing a Feature: `fgraph status` lists it under Removed with its reason.

Its work items are removed with it, for the same reason, and are on no line of their own. Run
end to end on a record in a temporary directory, through the file adapters of the package.
"""

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
import tomli_w

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_ALONE = ["add", "story", "a title", *CRITERION]
ADD_UNDER = [*ADD_ALONE, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
REMOVE = ["remove", "F-0001", "--reason", "filed by mistake"]
REMOVE_STORY = ["remove", "S-0001", "--reason", "superseded"]
# A started Feature whose one Story is started with it.
STARTED = (ADD_FEATURE, ADD_UNDER, ADD_TASK, ["start", "F-0001"])
BLOCK = ["block", "F-0001", "--reason", "a reason", "--waiting-on", "the sponsor"]
COMPLETE = [
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "abc1234"],
]
# A Feature never started and removed, with the one Story under it.
REMOVED = (ADD_FEATURE, ADD_UNDER, REMOVE)
GONE = "F-0001 is removed already"


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


def write_as_before(cwd: Path) -> None:
    """Rewrite the file of F-0001 as one written before a Feature had a state.

    It holds no state line and no started time, as the file of a Feature whose work items were
    started one by one.
    """
    path = cwd / ".fgraph" / "items" / "F-0001.toml"
    held = tomllib.loads(path.read_text("utf-8"))
    kept = {key: value for key, value in held.items() if key not in ("state", "started")}
    path.write_text(tomli_w.dumps(kept), "utf-8")


class TestAFeatureInBacklogWithAStoryUnderItRemovedWithAReason:
    @pytest.fixture
    def removed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *REMOVED)

    def test_remove_exits_with_zero(self, removed: Outcome) -> None:
        assert removed.status == 0

    def test_remove_names_the_feature(self, removed: Outcome) -> None:
        assert removed.out == "removed F-0001\n"

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

    def test_show_of_it_lists_its_reason_and_its_story_removed(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "F-0001"], tmp_path).out == (
            "F-0001  a feature title\n"
            "  bucket       Removed\n"
            "  reason       filed by mistake\n"
            "Criteria (1)\n"
            "  a criterion\n"
            "Work items (1)\n"
            "  S-0001  a title  Removed\n"
        )

    def test_its_story_is_removed_for_the_same_reason(
        self, removed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], tmp_path).out.splitlines()[1:4] == [
            "  bucket       Removed",
            "  parent       F-0001",
            "  reason       filed by mistake",
        ]


def test_a_removed_feature_is_listed_after_the_removed_work_items_and_none_of_its_own(
    tmp_path: Path,
) -> None:
    add_under = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
    listed = runs(tmp_path, ADD_ALONE, ADD_FEATURE, add_under, REMOVE_STORY, REMOVE, ["status"])
    assert listed.out.splitlines()[-3:] == [
        "Removed (2)",
        "  S-0001  a title  -- superseded",
        "  F-0001  a feature title  -- filed by mistake",
    ]


def test_a_story_of_it_removed_before_keeps_the_reason_it_had(tmp_path: Path) -> None:
    shown = runs(tmp_path, ADD_FEATURE, ADD_UNDER, REMOVE_STORY, REMOVE, ["show", "S-0001"])
    assert shown.out.splitlines()[3] == "  reason       superseded"


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([*STARTED, REMOVE], "F-0001 is started already"),
        ([*STARTED, BLOCK, REMOVE], "F-0001 is blocked"),
        ([*STARTED, *COMPLETE, REMOVE], "F-0001 is completed already"),
        ([*REMOVED, REMOVE], GONE),
        ([ADD_FEATURE, ["remove", "F-0001", "--reason", " "]], "reason is empty"),
        ([ADD_FEATURE, ["remove", "F-0009", "--reason", "why"]], "no Feature F-0009 in the record"),
        ([*REMOVED, ["start", "F-0001"]], GONE),
        ([*REMOVED, ["amend", "F-0001", "--title", "one more"]], GONE),
        ([*REMOVED, BLOCK], GONE),
        ([*REMOVED, ["unblock", "F-0001"]], "F-0001 is not blocked"),
        ([*REMOVED, ADD_UNDER], GONE),
        (
            [*REMOVED, ADD_ALONE, ["amend", "S-0002", "--parent", "F-0001"]],
            f"S-0002 cannot be put under F-0001: {GONE}",
        ),
        ([*REMOVED, ADD_TASK], "S-0001 is removed already"),
        (
            [*REMOVED, ADD_ALONE, ["reorder", "S-0002", "--before", "F-0001"]],
            "F-0001 is not in Backlog",
        ),
    ],
    ids=[
        "a-started-feature",
        "a-blocked-feature",
        "a-completed-feature",
        "removed-already",
        "blank-reason",
        "unknown-feature",
        "start-a-removed-feature",
        "amend-a-removed-feature",
        "block-a-removed-feature",
        "unblock-a-removed-feature",
        "story-added-under-a-removed-feature",
        "story-put-under-a-removed-feature",
        "task-for-a-story-removed-with-it",
        "reorder-before-a-removed-feature",
    ],
)
def test_a_remove_refused_or_a_move_of_a_removed_feature_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {error}"])


def test_a_feature_never_started_that_holds_a_started_story_is_not_removed(tmp_path: Path) -> None:
    runs(tmp_path, *STARTED)
    write_as_before(tmp_path)
    outcome = fgraph(REMOVE, tmp_path)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: F-0001 cannot be removed: S-0001 is started already"],
    )


def test_a_remove_refused_leaves_the_feature_and_its_story_as_they_were(tmp_path: Path) -> None:
    before = runs(tmp_path, ADD_FEATURE, ADD_UNDER, ["status"]).out
    assert runs(tmp_path, ["remove", "F-0001", "--reason", ""], ["status"]).out == before
