"""The criterion of completing a Feature: `fgraph status` lists it under Completed.

The completion of its last Story completes it, at the commit of that completion; the removal of
its last Story in Backlog completes nothing, and neither does the last Story of a Feature never
started. Run end to end on a record in a temporary directory, through the file adapters of the
package, each command one second after the one before it.
"""

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import tomli_w

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
LATER = START + timedelta(minutes=1)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
ADD_THIRD = ["add", "story", "a third title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
TWO_STORIES = (ADD_FEATURE, ADD_STORY, ADD_OTHER, ADD_TASK, TASK_FOR_OTHER)
FIRST_COMPLETED = (
    ["start", "F-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "def5678"],
)
# The completion of the first Story starts the second.
SECOND_READY = (
    ["start", "T-0002"],
    ["complete", "T-0002", "--commit", "1234abc"],
)
SECOND_AWAITED = (*TWO_STORIES, *FIRST_COMPLETED, *SECOND_READY)
COMPLETE_SECOND = ["complete", "S-0002", "--commit", "5678def"]
COMPLETED_ON = START + timedelta(seconds=len(SECOND_AWAITED))
KEPT_BEFORE = ("id", "title", "created", "criteria")


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


def feature_held(cwd: Path) -> dict[str, object]:
    """What the file of F-0001 in the record of cwd holds."""
    return tomllib.loads((cwd / ".fgraph" / "items" / "F-0001.toml").read_text("utf-8"))


def write_as_before(cwd: Path) -> None:
    """Rewrite the file of F-0001 as one written before a Feature had a state.

    It holds no state line and no started time, as the file of a Feature whose work items were
    started one by one.
    """
    kept = {key: value for key, value in feature_held(cwd).items() if key in KEPT_BEFORE}
    (cwd / ".fgraph" / "items" / "F-0001.toml").write_text(tomli_w.dumps(kept), "utf-8")


class TestTheSecondStoryOfAStartedFeatureCompletedAfterTheFirst:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *SECOND_AWAITED, COMPLETE_SECOND)

    def test_complete_exits_with_zero(self, completed: Outcome) -> None:
        assert completed.status == 0

    def test_complete_names_the_story_then_the_feature_each_at_that_commit(
        self, completed: Outcome
    ) -> None:
        assert completed.out == "completed S-0002 at 5678def\ncompleted F-0001 at 5678def\n"

    def test_status_lists_the_feature_under_completed_with_its_progress_and_that_commit(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "Backlog (0)\n"
            "InProgress (0)\n"
            "Completed (1)\n"
            "  F-0001  2/2 W  5678def  a feature title\n"
        )

    def test_show_of_the_feature_names_its_bucket_that_commit_and_the_bucket_of_each_story(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["show", "F-0001"], tmp_path, LATER).out == (
            "F-0001  a feature title\n"
            "  bucket       Completed\n"
            "  commit       5678def\n"
            "Criteria (1)\n"
            "  a criterion\n"
            "Work items (2)\n"
            "  S-0001  a title  Completed\n"
            "  S-0002  another title  Completed\n"
        )

    def test_the_file_of_the_feature_holds_its_state_its_completed_time_and_that_commit(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        held = feature_held(tmp_path)
        assert (held["state"], held["completed"], held["commit"]) == (
            "completed",
            COMPLETED_ON,
            "5678def",
        )

    @pytest.mark.parametrize(
        "argv", [["start", "F-0001"], ADD_THIRD], ids=["its-start", "a-story-added-under-it"]
    )
    def test_the_completed_feature_takes_neither_a_start_nor_a_story_added_under_it(
        self, argv: list[str], completed: Outcome, tmp_path: Path
    ) -> None:
        refused = fgraph(argv, tmp_path, LATER)
        assert (refused.status, refused.err.splitlines()[-1]) == (
            2,
            "fgraph: error: F-0001 is completed already",
        )


class TestAStoryOfAStartedFeatureCompletedWhileAnotherIsInBacklog:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *TWO_STORIES, *FIRST_COMPLETED)

    def test_complete_names_no_feature_completed(self, completed: Outcome) -> None:
        assert "F-0001" not in completed.out

    def test_status_lists_the_feature_under_in_progress(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out.splitlines()[1:3] == [
            "InProgress (1)",
            "  F-0001  1/2 W  a feature title",
        ]

    def test_the_file_of_the_feature_holds_it_started(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert feature_held(tmp_path)["state"] == "started"


def test_a_feature_whose_other_stories_are_completed_or_removed_completes_with_the_last(
    tmp_path: Path,
) -> None:
    remove = ["remove", "S-0003", "--reason", "not needed"]
    runs(tmp_path, *SECOND_AWAITED, ADD_THIRD, remove, COMPLETE_SECOND)
    assert fgraph(["status"], tmp_path, LATER).out.splitlines()[2:4] == [
        "Completed (1)",
        "  F-0001  2/2 W  5678def  a feature title",
    ]


def test_a_feature_completed_without_a_commit_is_listed_and_shown_without_one(
    tmp_path: Path,
) -> None:
    completed = runs(tmp_path, *SECOND_AWAITED, ["complete", "S-0002"])
    assert (
        completed.out,
        fgraph(["status"], tmp_path, LATER).out.splitlines()[3],
        fgraph(["show", "F-0001"], tmp_path, LATER).out.splitlines()[1:3],
    ) == (
        "completed S-0002\ncompleted F-0001\n",
        "  F-0001  2/2 W  a feature title",
        ["  bucket       Completed", "Criteria (1)"],
    )


class TestTheLastStoryOfAFeatureNeverStartedCompleted:
    """The file of the Feature holds no state line, as one written before a Feature had one."""

    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        runs(tmp_path, *SECOND_AWAITED)
        write_as_before(tmp_path)
        return fgraph(COMPLETE_SECOND, tmp_path, COMPLETED_ON)

    def test_complete_names_the_story_alone(self, completed: Outcome) -> None:
        assert completed.out == "completed S-0002 at 5678def\n"

    def test_status_lists_the_feature_under_completed_its_derived_bucket_without_a_commit(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "Backlog (0)\nInProgress (0)\nCompleted (1)\n  F-0001  2/2 W  a feature title\n"
        )

    def test_the_file_of_the_feature_is_left_without_a_state_line(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert tuple(feature_held(tmp_path)) == KEPT_BEFORE


# The first Story completed, the second left in Backlog with no Task, then removed.
LEFT_DONE = (
    ADD_FEATURE,
    ADD_STORY,
    ADD_OTHER,
    ADD_TASK,
    *FIRST_COMPLETED,
    ["remove", "S-0002", "--reason", "not needed"],
)


class TestAStartedFeatureLeftWithEveryStoryCompletedOrRemovedCompleted:
    @pytest.fixture
    def completed(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *LEFT_DONE, ["complete", "F-0001"])

    def test_complete_names_the_feature_at_the_commit_of_its_last_completed_story(
        self, completed: Outcome
    ) -> None:
        assert completed == Outcome(0, "completed F-0001 at def5678\n", "")

    def test_status_lists_the_feature_under_completed(
        self, completed: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out.splitlines()[2:4] == [
            "Completed (1)",
            "  F-0001  1/1 W  def5678  a feature title",
        ]


COMPLETE_FEATURE = ["complete", "F-0001"]


@pytest.mark.parametrize(
    ("argvs", "why"),
    [
        (
            (ADD_FEATURE, ADD_STORY, ADD_OTHER, ADD_TASK, *FIRST_COMPLETED, COMPLETE_FEATURE),
            "F-0001 cannot complete: S-0002 is in Backlog",
        ),
        ((ADD_FEATURE, ADD_STORY, COMPLETE_FEATURE), "F-0001 is in Backlog: start it first"),
        (
            (*LEFT_DONE, [*COMPLETE_FEATURE, "--commit", "abc1234"]),
            "F-0001 takes no --commit: it is completed at the commit of its last completed"
            " work item",
        ),
    ],
    ids=["a-story-in-backlog", "never-started", "a-commit-given"],
)
def test_a_complete_of_a_feature_refused_exits_with_two_naming_why(
    argvs: tuple[Sequence[str], ...], why: str, tmp_path: Path
) -> None:
    refused = runs(tmp_path, *argvs)
    assert (refused.status, refused.err.splitlines()[-1]) == (2, f"fgraph: error: {why}")
