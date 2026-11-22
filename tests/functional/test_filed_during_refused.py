"""What a work item filed during another asks: the id given at the add alone, refused when it
holds no work item or a removed one, kept in every state and shown from both sides.

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
ADD_BUG = ["add", "bug", "a bug title", "--observed", "it fails", "--expected", "it works"]
DURING = ["--filed-during", "S-0001"]
FILED = (ADD_STORY, [*ADD_BUG, *DURING])
TASK_FOR_BUG = ["add", "task", "a task title", "--parent", "B-0001", "--output", "an output"]


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
        (ADD_BUG, "B-0001"),
        (["add", "spike", "a title", "--hypothesis", "is it so?"], "Q-0001"),
    ],
    ids=["story", "upkeep", "bug", "spike"],
)
def test_each_kind_of_work_item_is_added_filed_during_another(
    add: list[str], item: str, tmp_path: Path
) -> None:
    shown = runs(tmp_path, ADD_STORY, [*add, *DURING], ["show", item]).out
    assert "  filed during S-0001\n" in shown


def test_show_of_the_other_lists_each_work_item_filed_during_it_in_the_order_of_the_record(
    tmp_path: Path,
) -> None:
    upkeep = ["add", "upkeep", "an upkeep title", *CRITERION, *DURING]
    shown = runs(tmp_path, *FILED, upkeep, ["show", "S-0001"]).out
    assert "  filed here   U-0001, B-0001\n" in shown


def test_show_of_a_work_item_nothing_was_filed_during_lists_none(tmp_path: Path) -> None:
    assert "filed here" not in runs(tmp_path, ADD_STORY, ["show", "S-0001"]).out


def test_show_of_a_work_item_not_filed_during_another_lists_none(tmp_path: Path) -> None:
    assert "filed during" not in runs(tmp_path, *FILED, ["show", "S-0001"]).out


def test_the_work_item_filed_during_is_kept_once_started(tmp_path: Path) -> None:
    started = [TASK_FOR_BUG, ["start", "B-0001"]]
    assert "  filed during S-0001\n" in runs(tmp_path, *FILED, *started, ["show", "B-0001"]).out


def test_the_work_item_filed_during_is_kept_once_completed(tmp_path: Path) -> None:
    done = [TASK_FOR_BUG, ["start", "B-0001"], ["start", "T-0001"]]
    done += [
        ["complete", "T-0001", "--commit", "abc1234"],
        ["complete", "B-0001", "--commit", "def5678"],
    ]
    assert "  filed during S-0001\n" in runs(tmp_path, *FILED, *done, ["show", "B-0001"]).out


def test_the_work_item_filed_during_is_kept_once_removed(tmp_path: Path) -> None:
    removed = ["remove", "B-0001", "--reason", "no longer"]
    assert "  filed during S-0001\n" in runs(tmp_path, *FILED, removed, ["show", "B-0001"]).out


def test_the_work_item_filed_during_is_kept_when_amended(tmp_path: Path) -> None:
    amend = ["amend", "B-0001", "--title", "another bug title"]
    assert "  filed during S-0001\n" in runs(tmp_path, *FILED, amend, ["show", "B-0001"]).out


def test_an_add_filed_during_a_work_item_the_record_holds_not_is_refused(tmp_path: Path) -> None:
    add = [*ADD_BUG, "--filed-during", "S-0009"]
    assert refused(runs(tmp_path, add)) == (2, "fgraph: error: no Story S-0009 in the record")


def test_an_add_refused_writes_nothing(tmp_path: Path) -> None:
    add = [*ADD_BUG, "--filed-during", "S-0009"]
    assert runs(tmp_path, add, ["show", "B-0001"]).status == 2


def test_an_add_filed_during_a_removed_work_item_is_refused(tmp_path: Path) -> None:
    setup = (ADD_STORY, ["remove", "S-0001", "--reason", "no longer"])
    expected = "fgraph: error: a work item cannot be filed during S-0001: it is removed"
    assert refused(runs(tmp_path, *setup, [*ADD_BUG, *DURING])) == (2, expected)


def test_an_add_filed_during_a_task_is_refused(tmp_path: Path) -> None:
    add = [*ADD_BUG, "--filed-during", "T-0001"]
    expected = "fgraph: error: 'T-0001' is no Story, Upkeep, Bug or Spike id"
    assert refused(runs(tmp_path, ADD_STORY, add)) == (2, expected)


def test_an_add_filed_during_a_feature_is_refused(tmp_path: Path) -> None:
    add = [*ADD_BUG, "--filed-during", "F-0001"]
    assert runs(tmp_path, ADD_STORY, add).status == 2


def test_an_amend_does_not_take_it(tmp_path: Path) -> None:
    amend = ["amend", "B-0001", "--filed-during", "S-0001"]
    with pytest.raises(SystemExit) as exited:
        runs(tmp_path, ADD_STORY, ADD_BUG, amend)
    assert exited.value.code == 2
