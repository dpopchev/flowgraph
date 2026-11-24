"""The criterion of putting a work item under a Feature: `fgraph show` of it lists the Story.

A Story standing alone is put under a Feature by `fgraph amend --parent`, both in Backlog. Run
end to end on a record in a temporary directory, through the file adapters of the package.
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
ADD_ALONE = ["add", "story", "a title", *CRITERION]
ADD_UNDER = [*ADD_ALONE, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
PUT_UNDER = ["amend", "S-0001", "--parent", "F-0001"]
TAKE_OUT = ["amend", "S-0001", "--parent", "none"]
SHOW = ["show", "S-0001"]
SHOW_FEATURE = ["show", "F-0001"]
# A started Feature whose first Story is started and whose second is in Backlog under it.
STARTED = (ADD_FEATURE, ADD_UNDER, ADD_TASK, ADD_UNDER, ["start", "F-0001"])


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


class TestAStoryStandingAlonePutUnderAFeatureBothInBacklog:
    @pytest.fixture
    def put_under(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, ADD_FEATURE, ADD_ALONE, PUT_UNDER)

    def test_amend_exits_with_zero(self, put_under: Outcome) -> None:
        assert put_under.status == 0

    def test_amend_names_the_story(self, put_under: Outcome) -> None:
        assert put_under.out == "amended S-0001\n"

    def test_show_of_the_feature_lists_the_story(self, put_under: Outcome, tmp_path: Path) -> None:
        assert fgraph(SHOW_FEATURE, tmp_path).out == (
            "F-0001  a feature title\n"
            "  bucket       Backlog\n"
            "Criteria (1)\n"
            "  a criterion\n"
            "Work items (1)\n"
            "  S-0001  a title  Backlog\n"
        )

    def test_show_of_the_story_names_the_feature_as_its_parent(
        self, put_under: Outcome, tmp_path: Path
    ) -> None:
        assert fgraph(SHOW, tmp_path).out.splitlines()[2] == "  parent       F-0001"


def test_a_story_taken_out_with_none_is_no_longer_listed_by_its_feature(tmp_path: Path) -> None:
    shown = runs(tmp_path, ADD_FEATURE, ADD_UNDER, TAKE_OUT, SHOW_FEATURE).out
    assert shown.splitlines()[-1] == "Work items (0)"


def test_a_story_taken_out_with_none_names_no_parent(tmp_path: Path) -> None:
    assert runs(tmp_path, ADD_FEATURE, ADD_UNDER, TAKE_OUT, SHOW).out.splitlines()[:3] == [
        "S-0001  a title",
        "  bucket       Backlog",
        "  given        a state",
    ]


def test_a_story_is_put_under_a_feature_beside_another_part_and_keeps_its_task(
    tmp_path: Path,
) -> None:
    amend = [*PUT_UNDER, "--title", "another title"]
    assert runs(tmp_path, ADD_FEATURE, ADD_ALONE, ADD_TASK, amend, SHOW).out == (
        "S-0001  another title\n"
        "  bucket       Backlog\n"
        "  parent       F-0001\n"
        "  given        a state\n"
        "  when         an action\n"
        "  then         another\n"
        "Tasks (1)\n"
        "  T-0001  a task title\n"
        "    expected output  an output\n"
    )


def test_a_story_put_under_the_feature_it_is_under_is_amended_and_stays(tmp_path: Path) -> None:
    before = runs(tmp_path, ADD_FEATURE, ADD_UNDER, SHOW).out
    amended = fgraph(PUT_UNDER, tmp_path)
    assert (amended.status, amended.out, fgraph(SHOW, tmp_path).out) == (
        0,
        "amended S-0001\n",
        before,
    )


def test_a_story_put_under_a_feature_keeps_the_place_the_queue_gave_it(tmp_path: Path) -> None:
    runs(
        tmp_path,
        ADD_FEATURE,
        ADD_UNDER,
        ADD_ALONE,
        ADD_ALONE,
        ["reorder", "S-0003", "--before", "S-0002"],
        ["amend", "S-0002", "--parent", "F-0001"],
        ["amend", "S-0003", "--parent", "F-0001"],
    )
    assert fgraph(SHOW_FEATURE, tmp_path).out.splitlines()[-3:] == [
        "  S-0003  a title  Backlog",
        "  S-0002  a title  Backlog",
        "  S-0001  a title  Backlog",
    ]


def test_a_story_taken_out_of_a_feature_keeps_the_place_the_queue_gave_it(tmp_path: Path) -> None:
    runs(
        tmp_path,
        ADD_FEATURE,
        ADD_UNDER,
        ADD_UNDER,
        ADD_ALONE,
        ["reorder", "S-0002", "--before", "S-0001"],
        ["reorder", "S-0003", "--before", "F-0001"],
        ["amend", "S-0002", "--parent", "none"],
    )
    assert fgraph(["status", "--backlog"], tmp_path).out.splitlines()[:4] == [
        "Backlog (3)",
        "> S-0003  []  a title",
        "  F-0001  0/1 W  a feature title",
        "  S-0002  []  a title",
    ]


def test_a_work_item_alone_is_put_under_a_started_feature_as_an_add_puts_it(
    tmp_path: Path,
) -> None:
    put = runs(tmp_path, *STARTED, ADD_ALONE, ["amend", "S-0003", "--parent", "F-0001"])
    assert (put.status, put.out) == (0, "amended S-0003\n")


@pytest.mark.parametrize(
    ("argvs", "error"),
    [
        (
            [*STARTED, ["amend", "S-0002", "--parent", "none"]],
            "S-0002 cannot be taken out of F-0001: F-0001 is started already",
        ),
        (
            [*STARTED, ADD_FEATURE, ["amend", "S-0002", "--parent", "F-0002"]],
            "S-0002 cannot be taken out of F-0001: F-0001 is started already",
        ),
        (
            [
                *STARTED,
                ["block", "F-0001", "--reason", "a reason", "--waiting-on", "the sponsor"],
                ["amend", "S-0002", "--parent", "none"],
            ],
            "S-0002 cannot be taken out of F-0001: F-0001 is blocked",
        ),
        (
            [ADD_FEATURE, ADD_ALONE, ["amend", "S-0001", "--parent", "F-0009"]],
            "no Feature F-0009 in the record",
        ),
        (
            [ADD_FEATURE, ADD_ALONE, ["amend", "S-0001", "--parent", "None"]],
            "'None' is neither a Feature id nor none: a Feature id is F- and a number",
        ),
        (
            [*STARTED, ["amend", "S-0001", "--parent", "none"]],
            "S-0001 is started: its complexity, its parent and what it depends on are amended in"
            " Backlog alone",
        ),
    ],
    ids=[
        "out-of-a-started-feature",
        "from-a-started-feature-to-another",
        "out-of-a-blocked-feature",
        "an-unknown-feature",
        "no-feature-id",
        "a-started-story",
    ],
)
def test_a_parent_refused_exits_with_two_and_names_why(
    argvs: list[list[str]], error: str, tmp_path: Path
) -> None:
    outcome = runs(tmp_path, *argvs)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {error}")


def test_a_parent_refused_leaves_the_story_as_it_was(tmp_path: Path) -> None:
    before = runs(tmp_path, *STARTED, ["show", "S-0002"]).out
    amend = ["amend", "S-0002", "--parent", "none", "--title", "another title"]
    assert runs(tmp_path, amend, ["show", "S-0002"]).out == before
