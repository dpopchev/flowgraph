"""fgraph about lists each relation that holds of an item under a heading and no other.

A work item lists its relations in both directions; a Feature lists its work items. Run end to end
on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from tests.functional.completed_story import ADD_TASK, COMPLETIONS

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
GATE = ["add", "term", "gate", "--means", "a check before a landing"]
FEATURE = [
    "add",
    "feature",
    "a feature title",
    "--criterion",
    "a developer sees it",
    "--about",
    "gate",
]
FIRST = ["add", "story", "the first title", *CRITERION, "--parent", "F-0001"]
SECOND = ["add", "story", "the second title", *CRITERION, "--depends-on", "S-0001"]
DURING = ["add", "story", "the third title", *CRITERION, "--filed-during", "S-0002"]
OLD = ["add", "story", "the old title", *CRITERION]
REMOVE_OLD = ["remove", "S-0005", "--superseded-by", "S-0002"]
COMPLETED_FIRST = [ADD_TASK, ["start", "F-0001"], *COMPLETIONS]
AMEND = ["add", "story", "the amending title", *CRITERION, "--amends", "S-0001"]
ALL = [GATE, FEATURE, FIRST, *COMPLETED_FIRST, SECOND, DURING, AMEND, OLD, REMOVE_OLD]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path) -> Outcome:
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


def about(item: str, cwd: Path) -> str:
    """The output of fgraph about of the item on a record of every kind of link."""
    for argv in ALL:
        fgraph(argv, cwd)
    return fgraph(["about", item], cwd).out


class TestTheWorkItemThatOthersDependOnAreFiledDuringAndSupersede:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> str:
        return about("S-0002", tmp_path)

    def test_the_head_is_its_id_and_its_title(self, listed: str) -> None:
        assert listed.splitlines()[0] == "S-0002  the second title"

    def test_it_lists_what_it_depends_on(self, listed: str) -> None:
        assert "  depends on (1)\n    S-0001  Completed  the first title\n" in listed

    def test_it_lists_what_was_filed_during_it(self, listed: str) -> None:
        assert "  filed here (1)\n    S-0003  Backlog  the third title\n" in listed

    def test_it_lists_what_it_supersedes_with_its_bucket(self, listed: str) -> None:
        assert "  supersedes (1)\n    S-0005  Removed  the old title\n" in listed

    def test_it_lists_no_relation_that_holds_of_nothing(self, listed: str) -> None:
        assert "feature" not in listed


class TestTheWorkItemThatOthersWaitFor:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> str:
        return about("S-0001", tmp_path)

    def test_it_lists_its_feature(self, listed: str) -> None:
        assert "  feature (1)\n    F-0001  Completed  a feature title\n" in listed

    def test_it_lists_the_work_items_that_depend_on_it(self, listed: str) -> None:
        assert "  depended on by (1)\n    S-0002  Backlog  the second title\n" in listed

    def test_it_lists_the_work_items_that_amend_it(self, listed: str) -> None:
        assert "  amended by (1)\n    S-0004  Backlog  the amending title\n" in listed


class TestTheWorkItemFiledDuringAnotherAndTheOneSuperseding:
    def test_it_lists_the_work_item_it_was_filed_during(self, tmp_path: Path) -> None:
        assert "  filed during (1)\n    S-0002  Backlog  the second title\n" in about(
            "S-0003", tmp_path
        )

    def test_it_lists_the_work_item_it_amends(self, tmp_path: Path) -> None:
        assert "  amends (1)\n    S-0001  Completed  the first title\n" in about("S-0004", tmp_path)

    def test_the_removed_one_lists_the_work_item_that_supersedes_it(self, tmp_path: Path) -> None:
        assert "  superseded by (1)\n    S-0002  Backlog  the second title\n" in about(
            "S-0005", tmp_path
        )


class TestAFeature:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> str:
        return about("F-0001", tmp_path)

    def test_the_head_is_its_id_and_its_title(self, listed: str) -> None:
        assert listed.splitlines()[0] == "F-0001  a feature title"

    def test_it_lists_its_work_items(self, listed: str) -> None:
        assert "  work items (1)\n    S-0001  Completed  the first title\n" in listed

    def test_it_lists_its_terms(self, listed: str) -> None:
        assert "  terms (1)\n    gate  a check before a landing\n" in listed


def test_an_item_that_holds_no_link_lists_its_head_alone(tmp_path: Path) -> None:
    fgraph(["add", "story", "alone", *CRITERION], tmp_path)
    assert fgraph(["about", "S-0001"], tmp_path).out == "S-0001  alone\n"
