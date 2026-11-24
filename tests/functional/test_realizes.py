"""The criterion of S-0100: a work item under a Feature names the criterion of it that it realizes.

`fgraph add --realizes N` and `fgraph amend --realizes N` name it, `fgraph show` lists it. Run end
to end on a record in a temporary directory, through the file adapters of the package.
"""

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
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
OTHER_FEATURE = ["add", "feature", "another feature", "--criterion", "its only criterion"]
UNDER = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
LINKED = [*UNDER, "--realizes", "2"]
ALONE = ["add", "story", "a title", *CRITERION]
TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
LINE = "  realizes     2  a second criterion"
ALONE_LINE = (
    "fgraph: error: --realizes names a criterion of the Feature a work item is under: "
    "this one stands alone"
)
NONE_SUCH = "fgraph: error: F-0001 has no criterion 3: its criteria count from 1 to 2"
BELOW = "fgraph: error: a criterion is counted from 1: 0 is below 1"
NO_NUMBER = "fgraph: error: --realizes 'two' is neither the number of a criterion nor none"
STARTED = (
    "fgraph: error: S-0001 is started: amend it with --deviation TEXT, "
    "what changes in what it was agreed to do"
)
NO_REALIZES = (
    "fgraph: error: F-0001 has no realizes: "
    "a Feature is amended by its title, its description and its criteria"
)
KINDS = {
    "upkeep": ("U-0001", ["add", "upkeep", "a title", *CRITERION]),
    "bug": ("B-0001", ["add", "bug", "a title", "--observed", "o", "--expected", "e"]),
    "spike": ("Q-0001", ["add", "spike", "a title", "--hypothesis", "is it so?"]),
}


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
    try:
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
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def realizes_lines(cwd: Path, item: str = "S-0001") -> list[str]:
    """The lines of `fgraph show` of the item that list what it realizes."""
    shown = fgraph(["show", item], cwd).out.splitlines()
    return [line for line in shown if line.startswith("  realizes")]


def held(cwd: Path) -> Any:
    """The file of S-0001 as TOML, indexed so that an absent key raises."""
    return tomllib.loads((cwd / ".fgraph" / "items" / "S-0001.toml").read_text())


def result(cwd: Path, *argvs: Sequence[str]) -> tuple[int, list[str]]:
    """The exit status and the realizes lines of S-0001, after the commands."""
    return runs(cwd, *argvs).status, realizes_lines(cwd)


def refusal(cwd: Path, *argvs: Sequence[str]) -> tuple[int, list[str]]:
    """The exit status and the last error line of the last command."""
    outcome = runs(cwd, *argvs)
    return outcome.status, outcome.err.splitlines()[-1:]


class TestAStoryAddedUnderAFeatureRealizingTheSecondCriterion:
    @pytest.fixture
    def added(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, FEATURE, LINKED)

    def test_add_exits_with_zero_and_names_the_story(self, added: Outcome) -> None:
        assert (added.status, added.out) == (0, "added S-0001\n")

    def test_show_lists_it_right_after_the_parent_line(
        self, added: Outcome, tmp_path: Path
    ) -> None:
        shown = fgraph(["show", "S-0001"], tmp_path).out.splitlines()
        assert shown[1:4] == ["  bucket       backlog", "  parent       F-0001", LINE]

    def test_its_file_holds_realizes_2(self, added: Outcome, tmp_path: Path) -> None:
        assert held(tmp_path)["realizes"] == 2


@pytest.mark.parametrize("kind", KINDS)
def test_an_add_of_each_other_kind_realizes_the_first_criterion(kind: str, tmp_path: Path) -> None:
    item, add = KINDS[kind]
    outcome = runs(tmp_path, FEATURE, [*add, "--parent", "F-0001", "--realizes", "1"])
    assert (outcome.status, realizes_lines(tmp_path, item)) == (
        0,
        ["  realizes     1  a first criterion"],
    )


def test_two_stories_may_realize_one_criterion(tmp_path: Path) -> None:
    assert runs(tmp_path, FEATURE, LINKED, LINKED).status == 0


def test_an_amend_gives_a_story_the_criterion(tmp_path: Path) -> None:
    assert result(tmp_path, FEATURE, UNDER, ["amend", "S-0001", "--realizes", "1"]) == (
        0,
        ["  realizes     1  a first criterion"],
    )


def test_an_amend_replaces_the_criterion_it_had(tmp_path: Path) -> None:
    assert result(tmp_path, FEATURE, LINKED, ["amend", "S-0001", "--realizes", "1"]) == (
        0,
        ["  realizes     1  a first criterion"],
    )


def test_an_amend_with_none_takes_the_criterion_away(tmp_path: Path) -> None:
    assert result(tmp_path, FEATURE, LINKED, ["amend", "S-0001", "--realizes", "none"]) == (0, [])


def test_an_add_with_none_names_no_criterion(tmp_path: Path) -> None:
    assert result(tmp_path, FEATURE, [*UNDER, "--realizes", "none"]) == (0, [])


def test_a_start_carries_the_criterion(tmp_path: Path) -> None:
    runs(tmp_path, FEATURE, LINKED, TASK, ["start", "F-0001"])
    assert realizes_lines(tmp_path) == [LINE]


def test_an_amend_to_another_parent_drops_the_criterion(tmp_path: Path) -> None:
    assert result(
        tmp_path, FEATURE, OTHER_FEATURE, LINKED, ["amend", "S-0001", "--parent", "F-0002"]
    ) == (0, [])


def test_an_amend_to_no_parent_drops_the_criterion(tmp_path: Path) -> None:
    assert result(
        tmp_path, FEATURE, OTHER_FEATURE, LINKED, ["amend", "S-0001", "--parent", "none"]
    ) == (0, [])


def test_an_amend_to_another_parent_keeps_the_criterion_given_with_it(tmp_path: Path) -> None:
    amend = ["amend", "S-0001", "--parent", "F-0002", "--realizes", "1"]
    assert result(tmp_path, FEATURE, OTHER_FEATURE, LINKED, amend) == (
        0,
        ["  realizes     1  its only criterion"],
    )


def test_an_amend_to_no_parent_with_a_criterion_is_refused(tmp_path: Path) -> None:
    amend = ["amend", "S-0001", "--parent", "none", "--realizes", "1"]
    assert refusal(tmp_path, FEATURE, OTHER_FEATURE, LINKED, amend) == (2, [ALONE_LINE])


def test_an_add_standing_alone_with_a_criterion_is_refused(tmp_path: Path) -> None:
    assert refusal(tmp_path, [*ALONE, "--realizes", "1"]) == (2, [ALONE_LINE])


def test_an_amend_of_a_story_standing_alone_with_a_criterion_is_refused(tmp_path: Path) -> None:
    assert refusal(tmp_path, ALONE, ["amend", "S-0001", "--realizes", "1"]) == (2, [ALONE_LINE])


def test_an_add_of_a_criterion_the_feature_does_not_have_is_refused(tmp_path: Path) -> None:
    assert refusal(tmp_path, FEATURE, [*UNDER, "--realizes", "3"]) == (2, [NONE_SUCH])


def test_an_amend_of_a_criterion_the_feature_does_not_have_is_refused(tmp_path: Path) -> None:
    assert refusal(tmp_path, FEATURE, UNDER, ["amend", "S-0001", "--realizes", "3"]) == (
        2,
        [NONE_SUCH],
    )


def test_a_criterion_below_one_is_refused(tmp_path: Path) -> None:
    assert refusal(tmp_path, FEATURE, [*UNDER, "--realizes", "0"]) == (2, [BELOW])


def test_a_word_that_is_no_number_is_refused(tmp_path: Path) -> None:
    assert refusal(tmp_path, FEATURE, [*UNDER, "--realizes", "two"]) == (2, [NO_NUMBER])


def test_a_started_story_is_not_amended_without_its_deviation(tmp_path: Path) -> None:
    amend = ["amend", "S-0001", "--realizes", "1"]
    assert refusal(tmp_path, FEATURE, UNDER, TASK, ["start", "F-0001"], amend) == (2, [STARTED])


def test_a_feature_is_not_amended_with_a_criterion_it_realizes(tmp_path: Path) -> None:
    assert refusal(tmp_path, FEATURE, ["amend", "F-0001", "--realizes", "1"]) == (2, [NO_REALIZES])


def test_an_amend_of_the_criteria_of_the_feature_leaves_the_number_as_written(
    tmp_path: Path,
) -> None:
    amend = ["amend", "F-0001", "--criterion", "a first criterion", "--criterion", "another second"]
    runs(tmp_path, FEATURE, LINKED, amend)
    assert realizes_lines(tmp_path) == ["  realizes     2  another second"]


def test_a_number_past_the_criteria_left_by_an_amend_names_none_of_them(tmp_path: Path) -> None:
    amend = ["amend", "F-0001", "--criterion", "only one"]
    runs(tmp_path, FEATURE, LINKED, amend)
    assert realizes_lines(tmp_path) == ["  realizes     2  none of the criteria of F-0001"]


class TestAStoryGivenNoCriterion:
    @pytest.fixture
    def added(self, tmp_path: Path) -> Outcome:
        return runs(tmp_path, FEATURE, UNDER)

    def test_show_lists_no_realizes_line(self, added: Outcome, tmp_path: Path) -> None:
        assert realizes_lines(tmp_path) == []

    def test_its_file_holds_no_key_realizes(self, added: Outcome, tmp_path: Path) -> None:
        assert "realizes" not in held(tmp_path)


def test_a_refused_add_writes_no_file(tmp_path: Path) -> None:
    runs(tmp_path, [*ALONE, "--realizes", "1"])
    assert not (tmp_path / ".fgraph" / "items" / "S-0001.toml").exists()
