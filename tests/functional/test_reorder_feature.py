"""The criterion of reordering a Feature: `fgraph status` lists it above the Story it precedes.

A Story under a Feature is reordered among the Stories of that Feature alone, as `fgraph show`
of the Feature lists them. Run end to end on a record in a temporary directory, through the file
adapters of the package, each command one second after the one before it.
"""

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title that stands alone", *CRITERION]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_INSIDE = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
REORDER = ["reorder", "F-0001", "--before", "S-0001"]
REORDER_INSIDE = ["reorder", "S-0003", "--before", "S-0002"]
UNDER = "S-0002 is under F-0001: it is reordered among the work items of F-0001 alone"


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


class TestAFeaturePutBeforeAStoryAddedBeforeIt:
    @pytest.fixture
    def reordered(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_FEATURE, REORDER)

    def test_reorder_exits_with_zero(self, reordered: Outcome) -> None:
        assert reordered.status == 0

    def test_status_lists_the_feature_before_the_story(
        self, reordered: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path, START + timedelta(minutes=1)).out == (
            "Backlog (2)\n"
            "  F-0001  0/0 W  a feature title\n"
            "  S-0001  a title that stands alone\n"
            "InProgress (0)\n"
            "Completed (0)\n"
        )


def shown_under_the_feature(cwd: Path) -> list[str]:
    """The lines `fgraph show F-0001` lists its two Stories on, in the order it lists them."""
    return fgraph(["show", "F-0001"], cwd, START + timedelta(minutes=1)).out.splitlines()[-2:]


class TestAStoryOfAFeaturePutBeforeAnotherOfIt:
    @pytest.fixture
    def reordered(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_FEATURE, ADD_INSIDE, ADD_OTHER, REORDER_INSIDE)

    def test_reorder_names_both_stories(self, reordered: Outcome) -> None:
        assert reordered.out == "moved S-0003 before S-0002\n"

    def test_show_of_the_feature_lists_it_above_the_other(
        self, reordered: Outcome, tmp_path: Path
    ) -> None:
        assert shown_under_the_feature(tmp_path) == [
            "  S-0003  another title  Backlog",
            "  S-0002  a title  Backlog",
        ]

    def test_a_reorder_of_the_feature_afterwards_keeps_the_order_of_its_stories(
        self, reordered: Outcome, tmp_path: Path
    ) -> None:
        fgraph(REORDER, tmp_path, START + timedelta(seconds=30))
        assert shown_under_the_feature(tmp_path) == [
            "  S-0003  another title  Backlog",
            "  S-0002  a title  Backlog",
        ]

    def test_the_queue_file_holds_the_feature_and_its_stories_in_one_list(
        self, reordered: Outcome, tmp_path: Path
    ) -> None:
        fgraph(REORDER, tmp_path, START + timedelta(seconds=30))
        held = tomllib.loads((tmp_path / ".fgraph" / "queue.toml").read_text("utf-8"))
        assert held == {"backlog": ["F-0001", "S-0001", "S-0003", "S-0002"]}


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        (
            [ADD_STORY, ADD_FEATURE, ADD_INSIDE, ADD_TASK, ["start", "S-0002"], REORDER],
            "F-0001 is not in Backlog",
        ),
        ([ADD_STORY, ["reorder", "S-0001", "--before", "F-0001"]], "F-0001 is not in Backlog"),
        (
            [ADD_STORY, ADD_FEATURE, ["reorder", "F-0001", "--before", "F-0001"]],
            "F-0001 cannot be put before itself",
        ),
        ([ADD_STORY, ADD_FEATURE, ADD_INSIDE, ["reorder", "S-0002", "--before", "S-0001"]], UNDER),
        ([ADD_STORY, ADD_FEATURE, ADD_INSIDE, ["reorder", "S-0002", "--before", "F-0001"]], UNDER),
        ([ADD_STORY, ADD_FEATURE, ADD_INSIDE, ["reorder", "S-0001", "--before", "S-0002"]], UNDER),
    ],
    ids=[
        "a-feature-in-progress",
        "before-a-feature-the-record-does-not-hold",
        "a-feature-before-itself",
        "a-story-of-a-feature-before-one-standing-alone",
        "a-story-of-a-feature-before-its-feature",
        "a-story-standing-alone-before-one-of-a-feature",
    ],
)
def test_a_reorder_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")
