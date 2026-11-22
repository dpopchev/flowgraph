"""The criterion of a work item command given the id of a Feature: it names every kind it takes.

`fgraph add task --parent` takes a Story, an Upkeep, a Bug and a Spike; `fgraph reorder`,
`fgraph amend` and `fgraph remove` take a Feature too (tests/functional/test_reorder_feature.py,
tests/functional/test_amend_feature.py, tests/functional/test_remove_feature.py). Run end to end
on a record in a temporary directory, through the file adapters of the package.
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
ADD_STORY = ["add", "story", "a title", *CRITERION]
REFUSAL = "fgraph: error: 'F-0001' is no Story, Upkeep, Bug or Spike id"


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


@pytest.mark.parametrize(
    "argv",
    [["add", "task", "a task title", "--parent", "F-0001", "--output", "an output"]],
    ids=["add-task-parent"],
)
def test_a_work_item_command_given_a_feature_id_exits_with_two_and_names_every_kind_it_takes(
    argv: list[str], tmp_path: Path
) -> None:
    outcome = runs(tmp_path, ADD_FEATURE, ADD_STORY, argv)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [REFUSAL])


@pytest.mark.parametrize(
    ("argv", "kinds"),
    [
        (["start", "X-1"], "Story, Upkeep, Bug, Spike, Task or Feature"),
        (["complete", "X-1"], "Story, Upkeep, Bug, Spike, Task or Feature"),
        (["amend", "X-1", "--title", "a title"], "Story, Upkeep, Bug, Spike or Feature"),
        (["remove", "X-1", "--reason", "a reason"], "Story, Upkeep, Bug, Spike or Feature"),
    ],
    ids=["start", "complete", "amend", "remove"],
)
def test_a_command_that_takes_a_feature_given_no_id_exits_with_two_and_names_the_feature_too(
    argv: list[str], kinds: str, tmp_path: Path
) -> None:
    outcome = fgraph(argv, tmp_path)
    named = f"fgraph: error: 'X-1' is no {kinds} id"
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [named])
