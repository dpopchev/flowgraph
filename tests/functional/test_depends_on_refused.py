"""What a work item that depends on another asks: its ids given at the add and the amend, refused
at the write when they hold no work item or close a cycle, and the start that waits for them.

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
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_UNDER = [*ADD_STORY, "--parent", "F-0001"]


def task_for(item: str) -> list[str]:
    """The command that writes a Task for the work item."""
    return ["add", "task", "a task title", "--parent", item, "--output", "an output"]


def depends(item: str, *ids: str) -> list[str]:
    """The command that makes the work item depend on those ids."""
    return ["amend", item, *(arg for each in ids for arg in ("--depends-on", each))]


def completes(item: str, task: str) -> list[list[str]]:
    """The commands that start the work item and complete its Task, then the item."""
    return [
        ["start", item],
        ["start", task],
        ["complete", task, "--commit", "abc1234"],
        ["complete", item, "--commit", "abc1234"],
    ]


# Three Stories in Backlog, each with a Task: S-0001, S-0002 and S-0003.
THREE = (
    ADD_STORY,
    ADD_STORY,
    ADD_STORY,
    task_for("S-0001"),
    task_for("S-0002"),
    task_for("S-0003"),
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


def refused(outcome: Outcome) -> tuple[int, str]:
    """The exit status of a run and the last line it wrote on the error output."""
    return outcome.status, outcome.err.splitlines()[-1]


@pytest.mark.parametrize(
    ("add", "item"),
    [
        (["add", "story", "a title", *CRITERION], "S-0002"),
        (["add", "upkeep", "a title", *CRITERION], "U-0001"),
        (["add", "bug", "a title", "--observed", "a", "--expected", "b"], "B-0001"),
        (["add", "spike", "a title", "--hypothesis", "is it so?"], "Q-0001"),
    ],
    ids=["story", "upkeep", "bug", "spike"],
)
def test_each_kind_of_work_item_is_added_depending_on_another(
    add: list[str], item: str, tmp_path: Path
) -> None:
    shown = runs(tmp_path, ADD_STORY, [*add, "--depends-on", "S-0001"], ["show", item]).out
    assert "  depends on   S-0001 (backlog)\n" in shown


def test_a_work_item_is_added_depending_on_several_in_the_order_given(tmp_path: Path) -> None:
    add = [*ADD_STORY, "--depends-on", "S-0002", "--depends-on", "S-0001"]
    shown = runs(tmp_path, ADD_STORY, ADD_STORY, add, ["show", "S-0003"]).out
    assert "  depends on   S-0002 (backlog), S-0001 (backlog)\n" in shown


def test_a_work_item_is_added_depending_on_one_of_another_kind(tmp_path: Path) -> None:
    upkeep = ["add", "upkeep", "a title", *CRITERION]
    shown = runs(tmp_path, upkeep, [*ADD_STORY, "--depends-on", "U-0001"], ["show", "S-0001"]).out
    assert "  depends on   U-0001 (backlog)\n" in shown


def test_show_lists_the_bucket_each_work_item_it_depends_on_is_in_now(tmp_path: Path) -> None:
    done = [*THREE, *completes("S-0001", "T-0001"), depends("S-0003", "S-0001", "S-0002")]
    shown = runs(tmp_path, *done, ["show", "S-0003"]).out
    assert "  depends on   S-0001 (completed), S-0002 (backlog)\n" in shown


def test_an_add_that_depends_on_a_work_item_the_record_holds_not_is_refused(
    tmp_path: Path,
) -> None:
    add = [*ADD_STORY, "--depends-on", "S-0009"]
    assert refused(runs(tmp_path, add)) == (2, "fgraph: error: no Story S-0009 in the record")


def test_an_add_refused_writes_nothing(tmp_path: Path) -> None:
    add = [*ADD_STORY, "--depends-on", "S-0009"]
    assert runs(tmp_path, add, ["show", "S-0001"]).status == 2


def test_the_ids_are_taken_away_by_none(tmp_path: Path) -> None:
    shown = runs(
        tmp_path, *THREE, depends("S-0002", "S-0001"), depends("S-0002", "none"), ["show", "S-0002"]
    ).out
    assert "depends on" not in shown


def test_the_ids_are_replaced_by_those_given(tmp_path: Path) -> None:
    shown = runs(
        tmp_path,
        *THREE,
        depends("S-0003", "S-0001"),
        depends("S-0003", "S-0002"),
        ["show", "S-0003"],
    ).out
    assert "  depends on   S-0002 (backlog)\n" in shown


@pytest.mark.parametrize(
    ("ids", "error"),
    [
        (["S-0009"], "no Story S-0009 in the record"),
        (["S-0001"], "S-0001 cannot depend on itself"),
        (["S-0002"], "a work item cannot depend on S-0002: it is removed"),
        (["T-0001"], "'T-0001' is no Story, Upkeep, Bug or Spike id"),
        (["S-0003", "none"], "none stands alone: it takes every dependency away"),
    ],
    ids=["unknown", "itself", "removed", "a-task", "none-with-an-id"],
)
def test_an_amend_refused_exits_with_two_and_names_why(
    ids: list[str], error: str, tmp_path: Path
) -> None:
    setup = (ADD_STORY, ADD_STORY, ADD_STORY, ["remove", "S-0002", "--reason", "no longer"])
    amend = depends("S-0001", *ids)
    assert refused(runs(tmp_path, *setup, amend)) == (2, f"fgraph: error: {error}")


def test_an_amend_refused_leaves_the_work_item_as_it_was(tmp_path: Path) -> None:
    before = runs(tmp_path, *THREE, depends("S-0001", "S-0002"), ["show", "S-0001"]).out
    assert runs(tmp_path, depends("S-0001", "S-0003", "S-0009"), ["show", "S-0001"]).out == before


def test_a_dependency_back_on_the_work_item_is_refused_as_a_cycle(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *THREE, depends("S-0002", "S-0001"), depends("S-0001", "S-0002"))
    expected = "fgraph: error: S-0001 cannot depend on S-0002: it would close a cycle"
    assert refused(outcome) == (2, expected)


def test_a_dependency_back_on_the_work_item_through_others_is_refused_as_a_cycle(
    tmp_path: Path,
) -> None:
    setup = (*THREE, depends("S-0002", "S-0001"), depends("S-0003", "S-0002"))
    expected = "fgraph: error: S-0001 cannot depend on S-0003: it would close a cycle"
    assert refused(runs(tmp_path, *setup, depends("S-0001", "S-0003"))) == (2, expected)


def test_a_work_item_started_is_amended_no_more(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *THREE, ["start", "S-0002"], depends("S-0002", "S-0001"))
    assert refused(outcome) == (
        2,
        "fgraph: error: S-0002 is started: its complexity, its parent and what it depends on are"
        " amended in Backlog alone",
    )


def test_a_feature_has_no_ids_to_depend_on(tmp_path: Path) -> None:
    outcome = runs(tmp_path, ADD_STORY, ADD_FEATURE, depends("F-0001", "S-0001"))
    assert outcome.err.splitlines()[-1].startswith("fgraph: error: F-0001 has no depends_on: ")


def test_the_start_of_a_work_item_names_each_one_it_waits_for_with_its_bucket(
    tmp_path: Path,
) -> None:
    setup = (*THREE, ["start", "S-0002"], depends("S-0003", "S-0001", "S-0002"))
    expected = (
        "fgraph: error: S-0003 cannot start: it depends on S-0001, in backlog;"
        " S-0002, in in-progress"
    )
    assert refused(runs(tmp_path, *setup, ["start", "S-0003"])) == (2, expected)


def test_the_start_refused_leaves_the_work_item_in_backlog(tmp_path: Path) -> None:
    setup = (*THREE, depends("S-0002", "S-0001"), ["start", "S-0002"])
    assert "  bucket       backlog\n" in runs(tmp_path, *setup, ["show", "S-0002"]).out


def test_the_start_is_taken_once_what_it_waits_for_is_completed(tmp_path: Path) -> None:
    setup = (*THREE, depends("S-0002", "S-0001"), *completes("S-0001", "T-0001"))
    assert runs(tmp_path, *setup, ["start", "S-0002"]).out == "started S-0002\n"


def test_the_start_of_a_work_item_that_depends_on_a_removed_one_is_refused(
    tmp_path: Path,
) -> None:
    setup = (*THREE, depends("S-0002", "S-0001"), ["remove", "S-0001", "--reason", "no longer"])
    expected = "fgraph: error: S-0002 cannot start: it depends on S-0001, in removed"
    assert refused(runs(tmp_path, *setup, ["start", "S-0002"])) == (2, expected)


def test_the_start_of_a_feature_is_refused_for_its_first_work_item_and_says_so(
    tmp_path: Path,
) -> None:
    setup = (ADD_STORY, ADD_FEATURE, ADD_UNDER, task_for("S-0002"), depends("S-0002", "S-0001"))
    expected = (
        "fgraph: error: F-0001 cannot start: its first work item S-0002 cannot start:"
        " it depends on S-0001, in backlog"
    )
    assert refused(runs(tmp_path, *setup, ["start", "F-0001"])) == (2, expected)


def test_the_next_work_item_a_completion_starts_is_left_in_backlog_and_says_so(
    tmp_path: Path,
) -> None:
    setup = (
        ADD_STORY,
        ADD_FEATURE,
        ADD_UNDER,
        ADD_UNDER,
        task_for("S-0002"),
        task_for("S-0003"),
        depends("S-0003", "S-0001"),
        ["start", "F-0001"],
        ["start", "T-0001"],
        ["complete", "T-0001", "--commit", "abc1234"],
    )
    done = runs(tmp_path, *setup, ["complete", "S-0002", "--commit", "abc1234"])
    assert done.out.splitlines()[-1] == (
        "not started: S-0003 cannot start: it depends on S-0001, in backlog"
    )
