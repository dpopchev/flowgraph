"""The criterion of reordering the Backlog: `fgraph status` lists a Story above the one it precedes.

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
ADD_OTHER = ["add", "story", "another title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
REORDER = ["reorder", "S-0002", "--before", "S-0001"]


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


class TestAStoryPutBeforeAnotherInBacklog:
    @pytest.fixture
    def reordered(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_OTHER, REORDER)

    def test_reorder_exits_with_zero(self, reordered: Outcome) -> None:
        assert reordered.status == 0

    def test_reorder_names_both_stories(self, reordered: Outcome) -> None:
        assert reordered.out == "moved S-0002 before S-0001\n"

    def test_status_lists_it_above_the_other(self, reordered: Outcome, tmp_path: Path) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (2)\n"
            "  S-0002  another title\n"
            "  S-0001  a title\n"
            "InProgress (0)\n"
            "Completed (0)\n"
        )

    def test_a_story_added_afterwards_is_listed_last(
        self, reordered: Outcome, tmp_path: Path
    ) -> None:
        assert runs(tmp_path, ADD_STORY, ["status"]).out.splitlines()[1:4] == [
            "  S-0002  another title",
            "  S-0001  a title",
            "  S-0003  a title",
        ]


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_STORY, REORDER], "S-0002 is not in Backlog"),
        (
            [ADD_STORY, ADD_OTHER, ["reorder", "S-0002", "--before", "S-0003"]],
            "S-0003 is not in Backlog",
        ),
        (
            [ADD_STORY, ADD_OTHER, ADD_TASK, ["start", "S-0001"], REORDER],
            "S-0001 is not in Backlog",
        ),
        (
            [ADD_STORY, ["reorder", "S-0001", "--before", "S-0001"]],
            "S-0001 cannot be put before itself",
        ),
        (
            [ADD_STORY, ["reorder", "T-0001", "--before", "S-0001"]],
            "'T-0001' is no Story, Upkeep, Bug or Spike id",
        ),
    ],
    ids=["unknown-item", "unknown-before", "before-a-started-story", "before-itself", "no-id"],
)
def test_a_reorder_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")
