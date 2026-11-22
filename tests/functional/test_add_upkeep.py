"""The criterion of adding an Upkeep: `fgraph status` lists it under Backlog beside the Stories.

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
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_UPKEEP = [
    *("add", "upkeep", "an upkeep title"),
    *("--given", "a behavior", "--when", "it runs", "--then", "it still holds"),
]


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


class TestAnUpkeepAddedToARecordWithOneStory:
    @pytest.fixture
    def added(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_UPKEEP)

    def test_add_exits_with_zero(self, added: Outcome) -> None:
        assert added.status == 0

    def test_add_names_the_upkeep(self, added: Outcome) -> None:
        assert added.out == "added U-0001\n"

    def test_status_lists_it_under_backlog_beside_the_story(
        self, added: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(["status"], tmp_path).out == (
            "Backlog (2)\n"
            "> S-0001  a title\n"
            "  U-0001  an upkeep title\n"
            "InProgress (0)\n"
            "Completed (0)\n"
        )

    def test_show_lists_its_bucket_and_criterion(self, added: Outcome, tmp_path: Path) -> None:
        assert fgraph(["show", "U-0001"], tmp_path).out == (
            "U-0001  an upkeep title\n"
            "  bucket       Backlog\n"
            "  given        a behavior\n"
            "  when         it runs\n"
            "  then         it still holds\n"
            "Tasks (0)\n"
        )


def test_a_second_upkeep_takes_the_next_id(tmp_path: Path) -> None:
    assert runs(tmp_path, ADD_UPKEEP, ADD_UPKEEP).out == "added U-0002\n"


def test_show_lists_the_description_of_an_upkeep(tmp_path: Path) -> None:
    outcome = runs(tmp_path, [*ADD_UPKEEP, "--description", "why"], ["show", "U-0001"])
    assert "  description  why\n" in outcome.out


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([[*ADD_UPKEEP[:-1], " "]], "then is empty"),
        ([["show", "U-0009"]], "no Upkeep U-0009 in the record"),
    ],
    ids=["blank-then", "unknown-upkeep"],
)
def test_a_refused_upkeep_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")
