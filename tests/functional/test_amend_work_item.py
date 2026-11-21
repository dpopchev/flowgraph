"""The criterion of amending a work item in Backlog: `fgraph show` prints the part rewritten.

Every other part is printed as it was. Run end to end on a record in a temporary directory,
through the file adapters of the package.
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
ADD_STORY = ["add", "story", "a title", *CRITERION, "--description", "why"]
ADD_UPKEEP = ["add", "upkeep", "a title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "ST-0001", "--output", "an output"]
AMEND = ["amend", "ST-0001"]
AMEND_THEN = [*AMEND, "--then", "a new state"]
SHOW = ["show", "ST-0001"]
COMPLETE = [
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "ST-0001", "--commit", "abc1234"],
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


class TestAStoryInBacklogAmendedWithAnotherThen:
    @pytest.fixture
    def amended(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_STORY, ADD_TASK, AMEND_THEN)

    def test_amend_exits_with_zero(self, amended: Outcome) -> None:
        assert amended.status == 0

    def test_amend_names_the_story(self, amended: Outcome) -> None:
        assert amended.out == "amended ST-0001\n"

    def test_show_prints_the_new_then_and_every_other_part_as_it_was(
        self, amended: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(SHOW, tmp_path).out == (
            "ST-0001  a title\n"
            "  bucket       Backlog\n"
            "  description  why\n"
            "  given        a state\n"
            "  when         an action\n"
            "  then         a new state\n"
            "Tasks (1)\n"
            "  T-0001  a task title\n"
            "    expected output  an output\n"
        )


@pytest.mark.parametrize(
    ("option", "text", "line"),
    [
        ("--title", "another title", "ST-0001  another title"),
        ("--description", "why not", "  description  why not"),
        ("--given", "a new state", "  given        a new state"),
        ("--when", "a new action", "  when         a new action"),
    ],
    ids=["title", "description", "given", "when"],
)
def test_each_other_part_is_rewritten_alone(
    option: str, text: str, line: str, tmp_path: Path
) -> None:
    before = runs(tmp_path, ADD_STORY, SHOW).out.splitlines()
    after = runs(tmp_path, [*AMEND, option, text], SHOW).out.splitlines()
    assert [new for old, new in zip(before, after, strict=True) if old != new] == [line]


def test_several_parts_are_rewritten_by_one_amend(tmp_path: Path) -> None:
    amend = [*AMEND, "--title", "another title", "--given", "a new state"]
    assert runs(tmp_path, ADD_STORY, amend, SHOW).out.splitlines()[:4] == [
        "ST-0001  another title",
        "  bucket       Backlog",
        "  description  why",
        "  given        a new state",
    ]


def test_a_blank_description_clears_it(tmp_path: Path) -> None:
    shown = runs(tmp_path, ADD_STORY, [*AMEND, "--description", ""], SHOW).out
    assert "description" not in shown


def test_an_upkeep_in_backlog_is_amended_as_a_story_is(tmp_path: Path) -> None:
    amend = ["amend", "U-0001", "--then", "it still holds"]
    shown = runs(tmp_path, ADD_UPKEEP, amend, ["show", "U-0001"]).out
    assert "  then         it still holds\n" in shown


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_STORY, [*AMEND, "--then", " "]], "then is empty"),
        ([ADD_STORY, [*AMEND, "--title", ""]], "title is empty"),
        ([ADD_STORY, AMEND], "amend rewrites no part of ST-0001: name one"),
        ([ADD_STORY, ADD_TASK, ["start", "ST-0001"], AMEND_THEN], "ST-0001 is started already"),
        (
            [ADD_STORY, ADD_TASK, ["start", "ST-0001"], *COMPLETE, AMEND_THEN],
            "ST-0001 is completed already",
        ),
        (
            [ADD_STORY, ADD_TASK, ["amend", "T-0001", "--then", "a new state"]],
            "'T-0001' is no Story, Upkeep, Bug or Spike id",
        ),
        (
            [ADD_STORY, ["amend", "ST-0002", "--then", "a new state"]],
            "no Story ST-0002 in the record",
        ),
    ],
    ids=[
        "blank-then",
        "blank-title",
        "no-part",
        "a-started-story",
        "a-completed-story",
        "a-task",
        "unknown-story",
    ],
)
def test_an_amend_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")


def test_an_amend_refused_leaves_the_story_as_it_was(tmp_path: Path) -> None:
    before = runs(tmp_path, ADD_STORY, SHOW).out
    assert runs(tmp_path, [*AMEND, "--title", "another title", "--then", " "], SHOW).out == before
