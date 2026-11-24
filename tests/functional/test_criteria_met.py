"""The criteria of a Feature in `fgraph show`: met k of n by the completed work items that realize.

A work item under a Feature names the criterion it realizes with --realizes; a criterion is met
when one of its work items is completed. Run through the file adapters of the package, each
command one second after the one before it.
"""

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
FEATURE = [
    "add",
    "feature",
    "a feature title",
    "--criterion",
    "a first criterion",
    "--criterion",
    "a second criterion",
]
FIRST = ["add", "story", "a title", *CRITERION, "--parent", "F-0001", "--realizes", "1"]
OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
ALSO_FIRST = [*OTHER, "--realizes", "1"]
TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
TASK_FOR_OTHER = ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"]
XFAIL = pytest.mark.xfail(
    strict=True, reason="S-0101: fgraph show of a Feature lists no criterion as met"
)


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


def criteria(cwd: Path) -> list[str]:
    """The lines of fgraph show F-0001 from Criteria ( up to, not including, Work items (."""
    shown = fgraph(["show", "F-0001"], cwd, LATER).out.splitlines()
    first = next(index for index, line in enumerate(shown) if line.startswith("Criteria ("))
    last = next(index for index, line in enumerate(shown) if line.startswith("Work items ("))
    return shown[first:last]


def work_items(cwd: Path) -> list[str]:
    """The lines of fgraph show F-0001 from the one that starts with Work items ( to its end."""
    shown = fgraph(["show", "F-0001"], cwd, LATER).out.splitlines()
    first = next(index for index, line in enumerate(shown) if line.startswith("Work items ("))
    return shown[first:]


@XFAIL
def test_a_criterion_realized_by_a_completed_story_is_met_in_show(tmp_path: Path) -> None:
    runs(tmp_path, FEATURE, FIRST, OTHER, TASK, TASK_FOR_OTHER, ["start", "F-0001"], *COMPLETIONS)
    assert criteria(tmp_path) == [
        "Criteria (2), met 1 of 2",
        "  1  met      a first criterion  S-0001",
        "  2  not met  a second criterion",
    ]


@XFAIL
def test_a_criterion_realized_by_a_story_in_backlog_is_listed_on_its_line_not_met(
    tmp_path: Path,
) -> None:
    runs(tmp_path, FEATURE, FIRST)
    assert criteria(tmp_path) == [
        "Criteria (2), met 0 of 2",
        "  1  not met  a first criterion  S-0001",
        "  2  not met  a second criterion",
    ]


@XFAIL
def test_a_criterion_realized_by_a_started_story_is_listed_on_its_line_not_met(
    tmp_path: Path,
) -> None:
    runs(tmp_path, FEATURE, FIRST, TASK, ["start", "F-0001"])
    assert criteria(tmp_path) == [
        "Criteria (2), met 0 of 2",
        "  1  not met  a first criterion  S-0001",
        "  2  not met  a second criterion",
    ]


@XFAIL
def test_two_stories_on_one_criterion_are_both_listed_and_one_completed_meets_it(
    tmp_path: Path,
) -> None:
    runs(
        tmp_path,
        FEATURE,
        FIRST,
        ALSO_FIRST,
        TASK,
        TASK_FOR_OTHER,
        ["start", "F-0001"],
        *COMPLETIONS,
    )
    assert criteria(tmp_path)[1] == "  1  met      a first criterion  S-0001, S-0002"


@XFAIL
def test_a_completed_story_verified_no_still_meets_its_criterion(tmp_path: Path) -> None:
    runs(
        tmp_path,
        FEATURE,
        FIRST,
        OTHER,
        TASK,
        TASK_FOR_OTHER,
        ["start", "F-0001"],
        *COMPLETIONS,
        ["verify", "S-0001", "--no", "it does not hold"],
    )
    assert criteria(tmp_path)[1] == "  1  met      a first criterion  S-0001"


@XFAIL
def test_the_feature_completed_by_its_last_story_shows_its_criteria_met_1_of_2(
    tmp_path: Path,
) -> None:
    runs(tmp_path, FEATURE, FIRST, TASK, ["start", "F-0001"], *COMPLETIONS)
    assert (
        fgraph(["show", "F-0001"], tmp_path, LATER).out.splitlines()[1],
        criteria(tmp_path)[0],
    ) == (
        "  bucket       Completed",
        "Criteria (2), met 1 of 2",
    )


def test_a_feature_none_of_whose_stories_names_a_criterion_lists_its_criteria_as_before(
    tmp_path: Path,
) -> None:
    runs(tmp_path, FEATURE, OTHER)
    assert criteria(tmp_path) == ["Criteria (2)", "  a first criterion", "  a second criterion"]


def test_a_removed_story_that_realized_a_criterion_is_not_listed_and_the_criteria_are_as_before(
    tmp_path: Path,
) -> None:
    runs(tmp_path, FEATURE, FIRST, OTHER, ["remove", "S-0001", "--reason", "not needed"])
    assert criteria(tmp_path) == ["Criteria (2)", "  a first criterion", "  a second criterion"]


def test_show_of_the_feature_exits_with_zero_on_the_first_record(tmp_path: Path) -> None:
    runs(tmp_path, FEATURE, FIRST, OTHER, TASK, TASK_FOR_OTHER, ["start", "F-0001"], *COMPLETIONS)
    assert fgraph(["show", "F-0001"], tmp_path, LATER).status == 0


def test_the_work_items_shown_on_the_first_record_keep_their_buckets(tmp_path: Path) -> None:
    runs(tmp_path, FEATURE, FIRST, OTHER, TASK, TASK_FOR_OTHER, ["start", "F-0001"], *COMPLETIONS)
    assert work_items(tmp_path) == [
        "Work items (2)",
        "  S-0001  a title  Completed",
        "  S-0002  another title  InProgress",
    ]


def test_the_completion_of_the_feature_by_its_only_story_says_what_it_says_today(
    tmp_path: Path,
) -> None:
    completed = runs(tmp_path, FEATURE, FIRST, TASK, ["start", "F-0001"], *COMPLETIONS)
    assert completed == Outcome(0, "completed S-0001 at def5678\ncompleted F-0001 at def5678\n", "")
