"""The criterion of starting a Feature: `fgraph status` lists it under InProgress.

Its first Story is started with it and listed under it; a Story of it does not start before it,
nor beside another started Story of it. Run end to end on a record in a temporary directory,
through the file adapters of the package, each command one second after the one before it.
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
TASK_FOR_THIRD = ["add", "task", "a task title", "--parent", "S-0003", "--output", "an output"]
TWO_STORIES = (ADD_FEATURE, ADD_STORY, ADD_OTHER, ADD_TASK, TASK_FOR_OTHER)
START_FEATURE = ["start", "F-0001"]
COMPLETE_FIRST = (
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "def5678"],
)
NOT_STARTED = "F-0001 is not started, start it first"


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


def feature_file(cwd: Path) -> Path:
    """The file of F-0001 in the record of cwd."""
    return cwd / ".fgraph" / "items" / "F-0001.toml"


def write_as_before(cwd: Path) -> None:
    """Rewrite the file of F-0001 as one written before a Feature had a state.

    It holds no state line and no started time, as the file of a Feature whose work items were
    started one by one.
    """
    held = tomllib.loads(feature_file(cwd).read_text("utf-8"))
    kept = {key: value for key, value in held.items() if key not in ("state", "started")}
    feature_file(cwd).write_text(tomli_w.dumps(kept), "utf-8")


class TestAFeatureInBacklogWithTwoStoriesEachWithATaskStarted:
    @pytest.fixture
    def started(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *TWO_STORIES, START_FEATURE)

    def test_start_exits_with_zero(self, started: Outcome) -> None:
        assert started.status == 0

    def test_start_names_the_feature_and_its_first_story(self, started: Outcome) -> None:
        assert started.out == "started F-0001 with S-0001\n"

    def test_status_lists_the_feature_under_in_progress_with_its_first_story_under_it(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  F-0001  0/2 W  a feature title\n"
            "    S-0001  0/1 T  a title\n"
            "Completed (0)\n"
        )

    def test_show_of_the_feature_names_its_bucket_and_that_of_each_story(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        shown = fgraph(["show", "F-0001"], tmp_path, LATER).out.splitlines()
        assert [shown[1], *shown[-2:]] == [
            "  bucket       InProgress",
            "  S-0001  a title  InProgress",
            "  S-0002  another title  Backlog",
        ]

    def test_the_file_of_the_feature_holds_its_state_and_its_started_time(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        held = tomllib.loads(feature_file(tmp_path).read_text("utf-8"))
        assert (held["state"], held["started"]) == ("started", START + timedelta(seconds=5))


def test_the_story_started_with_a_feature_is_the_first_in_the_order_of_the_queue(
    tmp_path: Path,
) -> None:
    reorder = ["reorder", "S-0002", "--before", "S-0001"]
    assert runs(tmp_path, *TWO_STORIES, reorder, START_FEATURE).out == (
        "started F-0001 with S-0002\n"
    )


class TestTheNextStoryOfAStartedFeatureStartedOnceTheFirstIsCompleted:
    @pytest.fixture
    def started(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, *TWO_STORIES, START_FEATURE, *COMPLETE_FIRST, ["start", "S-0002"])

    def test_start_names_the_story(self, started: Outcome) -> None:
        assert (started.status, started.out) == (0, "started S-0002\n")

    def test_status_lists_it_under_the_feature_in_progress(
        self, started: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, LATER).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  F-0001  1/2 W  a feature title\n"
            "    S-0002  0/1 T  another title\n"
            "Completed (0)\n"
        )


def test_a_started_feature_whose_stories_are_all_completed_or_removed_is_listed_completed(
    tmp_path: Path,
) -> None:
    remove = ["remove", "S-0002", "--reason", "not needed"]
    runs(tmp_path, *TWO_STORIES, START_FEATURE, *COMPLETE_FIRST, remove)
    assert fgraph(["status"], tmp_path, LATER).out.splitlines()[2:4] == [
        "Completed (1)",
        "  F-0001  1/1 W  a feature title",
    ]


class TestAFeatureWrittenBeforeItHadAStateThatHoldsACompletedStory:
    """The file of the Feature holds no state line; S-0003 is placed before S-0002 in the queue."""

    @pytest.fixture
    def record(self, tmp_path: Path) -> Path:
        reorder = ["reorder", "S-0003", "--before", "S-0002"]
        added = (*TWO_STORIES, ADD_THIRD, TASK_FOR_THIRD, reorder)
        runs(tmp_path, *added, START_FEATURE, *COMPLETE_FIRST)
        write_as_before(tmp_path)
        return tmp_path

    def test_status_lists_it_in_its_derived_bucket(self, record: Path) -> None:
        assert fgraph(["status"], record, LATER).out == (
            "Backlog (0)\nInProgress (1)\n  F-0001  1/3 W  a feature title\nCompleted (0)\n"
        )

    def test_a_story_of_it_is_not_started_before_it(self, record: Path) -> None:
        refused = fgraph(["start", "S-0003"], record, LATER)
        assert (refused.status, refused.err.splitlines()[-1]) == (
            2,
            f"fgraph: error: S-0003 cannot start: {NOT_STARTED}",
        )

    def test_its_start_starts_its_next_story_in_backlog_in_the_order_of_the_queue(
        self, record: Path
    ) -> None:
        started = fgraph(START_FEATURE, record, LATER)
        assert (started.status, started.out) == (0, "started F-0001 with S-0003\n")

    def test_status_lists_it_under_in_progress_with_that_story_once_it_is_started(
        self, record: Path
    ) -> None:
        fgraph(START_FEATURE, record, LATER)
        assert fgraph(["status"], record, LATER).out == (
            "Backlog (0)\n"
            "InProgress (1)\n"
            "  F-0001  1/3 W  a feature title\n"
            "    S-0003  0/1 T  a third title\n"
            "Completed (0)\n"
        )


def test_the_tasks_and_the_completion_of_a_started_story_take_a_feature_never_started(
    tmp_path: Path,
) -> None:
    runs(tmp_path, *TWO_STORIES, START_FEATURE)
    write_as_before(tmp_path)
    written = [fgraph(argv, tmp_path, LATER).status for argv in COMPLETE_FIRST]
    assert written == [0, 0, 0]


def test_a_feature_start_refused_leaves_the_feature_in_backlog(tmp_path: Path) -> None:
    runs(tmp_path, ADD_FEATURE, ADD_STORY, ADD_OTHER, TASK_FOR_OTHER, START_FEATURE)
    assert fgraph(["status"], tmp_path, LATER).out == (
        "Backlog (1)\n  F-0001  0/2 W  a feature title\nInProgress (0)\nCompleted (0)\n"
    )


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_FEATURE, START_FEATURE], "F-0001 has no work item in Backlog to start with"),
        (
            [ADD_FEATURE, ADD_STORY, START_FEATURE],
            "F-0001 cannot start: S-0001 has no Task to start with",
        ),
        ([*TWO_STORIES, START_FEATURE, START_FEATURE], "F-0001 is started already"),
        ([START_FEATURE], "no Feature F-0001 in the record"),
        ([*TWO_STORIES, ["start", "S-0001"]], f"S-0001 cannot start: {NOT_STARTED}"),
        (
            [*TWO_STORIES, START_FEATURE, ["start", "S-0002"]],
            "S-0002 cannot start: F-0001 starts one work item at a time, started already: S-0001",
        ),
    ],
    ids=[
        "a-feature-without-a-work-item",
        "a-feature-whose-first-story-has-no-task",
        "a-feature-started-twice",
        "a-feature-the-record-does-not-hold",
        "a-story-before-its-feature",
        "a-story-beside-a-started-one-of-its-feature",
    ],
)
def test_a_start_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")
