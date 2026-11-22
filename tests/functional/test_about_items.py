"""An item and a knowledge line name the terms they are about: added, amended, noted and shown.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer sees it"]
ABOUT_GATE = ["--about", "gate"]
GATE = ["add", "term", "gate", "--means", "a check before a landing"]
LANE = ["add", "term", "lane", "--means", "one work item in its own worktree"]


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


@pytest.fixture
def terms(tmp_path: Path) -> Path:
    """A record with the terms gate and lane."""
    fgraph(GATE, tmp_path)
    fgraph(LANE, tmp_path)
    return tmp_path


class TestAWorkItemAddedAboutTerms:
    @pytest.fixture
    def added(self, terms: Path) -> Outcome:
        return fgraph([*ADD_STORY, *ABOUT_GATE, "--about", "lane"], terms)

    def test_add_exits_with_zero(self, added: Outcome) -> None:
        assert added.status == 0

    def test_show_of_it_lists_the_terms_once_per_term_in_order(
        self, added: Outcome, terms: Path
    ) -> None:
        assert "  about        gate, lane\n" in fgraph(["show", "S-0001"], terms).out


def test_a_feature_added_about_a_term_is_shown_with_it(terms: Path) -> None:
    fgraph([*ADD_FEATURE, *ABOUT_GATE], terms)
    assert "  about        gate\n" in fgraph(["show", "F-0001"], terms).out


def test_a_work_item_added_about_no_term_is_shown_with_none(terms: Path) -> None:
    fgraph(ADD_STORY, terms)
    assert "about" not in fgraph(["show", "S-0001"], terms).out


class TestAWorkItemAmendedAboutTerms:
    @pytest.fixture
    def amended(self, terms: Path) -> Outcome:
        fgraph([*ADD_STORY, *ABOUT_GATE], terms)
        return fgraph(["amend", "S-0001", "--about", "lane"], terms)

    def test_amend_exits_with_zero(self, amended: Outcome) -> None:
        assert amended.status == 0

    def test_show_of_it_lists_the_terms_given_in_place_of_those_it_had(
        self, amended: Outcome, terms: Path
    ) -> None:
        assert "  about        lane\n" in fgraph(["show", "S-0001"], terms).out

    def test_amend_about_none_takes_every_term_away(self, amended: Outcome, terms: Path) -> None:
        fgraph(["amend", "S-0001", "--about", "none"], terms)
        assert "about" not in fgraph(["show", "S-0001"], terms).out


def test_a_feature_amended_about_a_term_is_shown_with_it(terms: Path) -> None:
    fgraph(ADD_FEATURE, terms)
    fgraph(["amend", "F-0001", "--about", "lane"], terms)
    assert "  about        lane\n" in fgraph(["show", "F-0001"], terms).out


class TestALineNotedAboutTerms:
    @pytest.fixture
    def noted(self, terms: Path) -> Outcome:
        fgraph(ADD_STORY, terms)
        return fgraph(
            ["note", "S-0001", "--finding", "a text", *ABOUT_GATE, "--about", "lane"], terms
        )

    def test_note_exits_with_zero(self, noted: Outcome) -> None:
        assert noted.status == 0

    def test_show_of_the_item_lists_the_line_with_its_terms(
        self, noted: Outcome, terms: Path
    ) -> None:
        assert "  finding  2026-01-01  a text  (about gate, lane)\n" in (
            fgraph(["show", "S-0001"], terms).out
        )


def test_a_line_noted_on_a_feature_about_a_term_is_shown_with_it(terms: Path) -> None:
    fgraph(ADD_FEATURE, terms)
    fgraph(["note", "F-0001", "--decision", "a text", *ABOUT_GATE], terms)
    assert "  decision  2026-01-01  a text  (about gate)\n" in fgraph(["show", "F-0001"], terms).out


class TestTheShowOfATermWithItemsAndLinesAboutIt:
    @pytest.fixture
    def shown(self, terms: Path) -> Outcome:
        fgraph([*ADD_STORY, *ABOUT_GATE], terms)
        fgraph([*ADD_FEATURE, *ABOUT_GATE], terms)
        fgraph(["add", "story", "another", *CRITERION, "--about", "lane"], terms)
        fgraph(["note", "S-0001", "--finding", "about the gate", *ABOUT_GATE], terms)
        fgraph(["note", "F-0001", "--finding", "about the lane", "--about", "lane"], terms)
        return fgraph(["show", "gate"], terms)

    def test_it_lists_the_items_about_it_after_its_relations(self, shown: Outcome) -> None:
        assert "  added  2026-01-01\n  items  S-0001, F-0001\n" in shown.out

    def test_it_lists_the_lines_about_it_each_with_the_id_of_its_item(self, shown: Outcome) -> None:
        assert shown.out.endswith("  knowledge\n    S-0001  finding  2026-01-01  about the gate\n")


def test_the_show_of_a_term_nothing_is_about_lists_no_items_and_no_lines(terms: Path) -> None:
    assert fgraph(["show", "gate"], terms).out == (
        "gate\n  means  a check before a landing\n  added  2026-01-01\n"
    )


class TestTheKnowledgeListNarrowedToATerm:
    @pytest.fixture
    def listed(self, terms: Path) -> Outcome:
        fgraph(ADD_STORY, terms)
        fgraph(["note", "S-0001", "--finding", "about the gate", *ABOUT_GATE], terms)
        fgraph(["note", "S-0001", "--finding", "about the lane", "--about", "lane"], terms)
        fgraph(["note", "S-0001", "--finding", "about nothing"], terms)
        return fgraph(["knowledge", "--about", "gate"], terms)

    def test_it_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_it_lists_the_lines_about_the_term_alone(self, listed: Outcome) -> None:
        assert listed.out == "2026-01-01  finding  S-0001  about the gate  (about gate)\n"


def test_the_knowledge_list_of_a_term_no_line_is_about_says_there_are_none(terms: Path) -> None:
    assert fgraph(["knowledge", "--about", "gate"], terms).out == (
        "no knowledge lines about gate in the record\n"
    )


def test_the_knowledge_list_narrowed_to_a_term_not_in_the_record_is_refused(terms: Path) -> None:
    refused = fgraph(["knowledge", "--about", "nope"], terms)
    assert (refused.status, refused.err.splitlines()[-1]) == (
        2,
        "fgraph: error: no term 'nope' in the record: add it with fgraph add term",
    )
