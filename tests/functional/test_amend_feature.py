"""The criterion of amending a Feature in Backlog: `fgraph show` of it lists the new title.

Every other part is listed as it was. Run end to end on a record in a temporary directory,
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
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_DESCRIBED = [*ADD_FEATURE, "--criterion", "another", "--description", "why"]
ADD_ALONE = ["add", "story", "a title", *CRITERION]
ADD_UNDER = [*ADD_ALONE, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
AMEND = ["amend", "F-0001"]
AMEND_TITLE = [*AMEND, "--title", "another title"]
SHOW = ["show", "F-0001"]
# A started Feature whose one Story is started with it.
STARTED = (ADD_FEATURE, ADD_UNDER, ADD_TASK, ["start", "F-0001"])
BLOCK = ["block", "F-0001", "--reason", "a reason", "--waiting-on", "the sponsor"]
COMPLETE = [
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "abc1234"],
]
NEEDED = (
    "F-0001 is started: amend it with --deviation TEXT, what changes in what it was agreed to do"
)
ONLY_A_FEATURE = "a Feature is amended by its title, its description and its criteria"


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


class TestAFeatureInBacklogAmendedWithANewTitle:
    @pytest.fixture
    def amended(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_FEATURE, AMEND_TITLE)

    def test_amend_exits_with_zero(self, amended: Outcome) -> None:
        assert amended.status == 0

    def test_amend_names_the_feature(self, amended: Outcome) -> None:
        assert amended.out == "amended F-0001\n"

    def test_show_lists_the_new_title_and_every_other_part_as_it_was(
        self, amended: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(SHOW, tmp_path).out == (
            "F-0001  another title\n"
            "  bucket       backlog\n"
            "Criteria (1)\n"
            "  a criterion\n"
            "Work items (0)\n"
        )


def test_the_criteria_given_replace_the_ones_it_had_and_its_story_stays_under_it(
    tmp_path: Path,
) -> None:
    amend = [*AMEND, "--criterion", "a new one", "--criterion", "a second", "--description", ""]
    assert runs(tmp_path, ADD_DESCRIBED, ADD_UNDER, amend, SHOW).out == (
        "F-0001  a feature title\n"
        "  bucket       backlog\n"
        "Criteria (2)\n"
        "  a new one\n"
        "  a second\n"
        "Work items (1)\n"
        "  S-0001  a title  backlog\n"
    )


def test_a_feature_amended_keeps_the_place_the_queue_gave_it(tmp_path: Path) -> None:
    reorder = ["reorder", "F-0001", "--before", "S-0001"]
    listed = runs(
        tmp_path, ADD_ALONE, ADD_FEATURE, reorder, AMEND_TITLE, ["status", "--backlog"]
    ).out
    assert listed.splitlines()[:3] == [
        "backlog (2)",
        "  F-0001  0/0 W  another title",
        "> S-0001  []  a title",
    ]


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        ([ADD_FEATURE, [*AMEND, "--title", " "]], "title is empty"),
        ([ADD_FEATURE, [*AMEND, "--criterion", "a new", "--criterion", ""]], "criterion is empty"),
        ([ADD_FEATURE, AMEND], "amend rewrites no part of F-0001: name one"),
        ([ADD_FEATURE, [*AMEND, "--then", "a state"]], f"F-0001 has no then: {ONLY_A_FEATURE}"),
        (
            [ADD_FEATURE, [*AMEND_TITLE, "--parent", "none"]],
            f"F-0001 has no parent: {ONLY_A_FEATURE}",
        ),
        ([*STARTED, AMEND_TITLE], NEEDED),
        ([*STARTED, BLOCK, AMEND_TITLE], NEEDED),
        ([*STARTED, *COMPLETE, AMEND_TITLE], "F-0001 is completed already"),
        ([ADD_FEATURE, ["amend", "F-0009", "--title", "new"]], "no Feature F-0009 in the record"),
        (
            [ADD_ALONE, ["amend", "S-0001", "--criterion", "a criterion"]],
            "S-0001 has no criteria: only a Feature states them",
        ),
    ],
    ids=[
        "blank-title",
        "blank-criterion",
        "no-part",
        "a-part-of-a-criterion",
        "a-parent",
        "a-started-feature",
        "a-blocked-feature",
        "a-completed-feature",
        "unknown-feature",
        "criteria-of-a-story",
    ],
)
def test_an_amend_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")


def test_an_amend_refused_leaves_the_feature_as_it_was(tmp_path: Path) -> None:
    before = runs(tmp_path, ADD_DESCRIBED, SHOW).out
    assert runs(tmp_path, [*AMEND_TITLE, "--criterion", " "], SHOW).out == before
