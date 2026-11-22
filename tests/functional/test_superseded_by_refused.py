"""What a remove superseded by another asks: the id given, beside a reason or alone, refused when
it names no work item, the work item itself or a removed one, and shown from both sides.

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
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "it works"]
TWO = (ADD_STORY, ADD_OTHER)
SUPERSEDE = ["remove", "S-0001", "--superseded-by", "S-0002"]


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


def test_show_of_the_removed_work_item_lists_what_supersedes_it(tmp_path: Path) -> None:
    assert "  superseded by S-0002\n" in runs(tmp_path, *TWO, SUPERSEDE, ["show", "S-0001"]).out


def test_status_lists_what_supersedes_it_before_a_reason_given_beside_it(tmp_path: Path) -> None:
    remove = [*SUPERSEDE, "--reason", "refiled"]
    listed = runs(tmp_path, *TWO, remove, ["status"]).out
    assert "  S-0001  a title  -- superseded by S-0002, refiled\n" in listed


def test_show_lists_the_reason_given_beside_what_supersedes_it(tmp_path: Path) -> None:
    remove = [*SUPERSEDE, "--reason", "refiled"]
    assert "  reason       refiled\n" in runs(tmp_path, *TWO, remove, ["show", "S-0001"]).out


def test_show_of_the_other_lists_each_work_item_that_names_it_in_the_order_of_the_record(
    tmp_path: Path,
) -> None:
    third = ["add", "story", "a third title", *CRITERION]
    setup = (*TWO, third, SUPERSEDE, ["remove", "S-0003", "--superseded-by", "S-0002"])
    assert "  supersedes   S-0001, S-0003\n" in runs(tmp_path, *setup, ["show", "S-0002"]).out


def test_show_of_a_work_item_that_supersedes_none_lists_none(tmp_path: Path) -> None:
    assert "supersedes" not in runs(tmp_path, *TWO, SUPERSEDE, ["show", "S-0001"]).out


def test_the_work_item_that_supersedes_is_kept_in_the_file_of_the_removed_one(
    tmp_path: Path,
) -> None:
    runs(tmp_path, *TWO, SUPERSEDE)
    held = (tmp_path / ".fgraph" / "items" / "S-0001.toml").read_text(encoding="utf-8")
    assert 'superseded_by = "S-0002"\n' in held


def test_the_file_of_the_other_holds_nothing_of_it(tmp_path: Path) -> None:
    runs(tmp_path, *TWO, SUPERSEDE)
    held = (tmp_path / ".fgraph" / "items" / "S-0002.toml").read_text(encoding="utf-8")
    assert "S-0001" not in held


def test_a_remove_with_neither_a_reason_nor_what_supersedes_it_is_refused_naming_both(
    tmp_path: Path,
) -> None:
    expected = "fgraph: error: a remove takes --reason or --superseded-by, or both"
    assert refused(runs(tmp_path, ADD_STORY, ["remove", "S-0001"])) == (2, expected)


def test_a_remove_of_a_work_item_superseded_by_a_work_item_the_record_holds_not_is_refused(
    tmp_path: Path,
) -> None:
    remove = ["remove", "S-0001", "--superseded-by", "S-0009"]
    assert refused(runs(tmp_path, *TWO, remove)) == (
        2,
        "fgraph: error: no Story S-0009 in the record",
    )


def test_a_remove_of_a_work_item_superseded_by_itself_is_refused(tmp_path: Path) -> None:
    remove = ["remove", "S-0001", "--superseded-by", "S-0001"]
    expected = "fgraph: error: S-0001 cannot be superseded by itself"
    assert refused(runs(tmp_path, *TWO, remove)) == (2, expected)


def test_a_remove_of_a_work_item_superseded_by_a_removed_one_is_refused(tmp_path: Path) -> None:
    setup = (*TWO, ["remove", "S-0002", "--reason", "no longer"])
    expected = "fgraph: error: a work item cannot be superseded by S-0002: it is removed"
    assert refused(runs(tmp_path, *setup, SUPERSEDE)) == (2, expected)


def test_a_remove_superseded_by_a_work_item_that_is_no_id_is_refused(tmp_path: Path) -> None:
    remove = ["remove", "S-0001", "--superseded-by", "T-0001"]
    expected = "fgraph: error: 'T-0001' is no Story, Upkeep, Bug or Spike id"
    assert refused(runs(tmp_path, *TWO, remove)) == (2, expected)


def test_a_refused_remove_writes_nothing(tmp_path: Path) -> None:
    remove = ["remove", "S-0001", "--superseded-by", "S-0009"]
    assert "removed" not in runs(tmp_path, *TWO, remove, ["show", "S-0001"]).out


def test_the_remove_of_a_feature_takes_a_reason_alone(tmp_path: Path) -> None:
    remove = ["remove", "F-0001", "--superseded-by", "S-0001", "--reason", "a reason"]
    expected = "fgraph: error: F-0001 is a Feature: it is removed with --reason alone"
    assert refused(runs(tmp_path, ADD_STORY, ADD_FEATURE, remove)) == (2, expected)


def test_the_remove_of_a_feature_with_a_reason_is_as_before(tmp_path: Path) -> None:
    remove = ["remove", "F-0001", "--reason", "a reason"]
    assert runs(tmp_path, ADD_FEATURE, remove).out == "removed F-0001\n"
