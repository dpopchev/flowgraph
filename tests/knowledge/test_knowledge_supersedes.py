"""The lines a knowledge line supersedes: kept on it by their refs, and how a view ends a line."""

from datetime import UTC, datetime

import pytest

from flowgraph.knowledge import (
    DECISION,
    knowledge_row,
    line_ref,
    make_knowledge_line,
    superseded_text,
)

pytestmark = pytest.mark.model

NOTED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
REFS = ("S-0001#1", "S-0002#3")


def test_a_line_made_with_no_refs_supersedes_none() -> None:
    assert make_knowledge_line(DECISION, "a text", NOTED).supersedes == ()


def test_a_line_made_with_refs_holds_them_in_order() -> None:
    assert make_knowledge_line(DECISION, "a text", NOTED, supersedes=REFS).supersedes == REFS


def test_the_row_of_a_line_lists_the_refs_it_supersedes() -> None:
    line = make_knowledge_line(DECISION, "a text", NOTED, supersedes=REFS)
    assert knowledge_row(line).supersedes == list(REFS)


def test_the_row_of_a_line_is_superseded_by_none_as_the_item_holds_it() -> None:
    line = make_knowledge_line(DECISION, "a text", NOTED, supersedes=REFS)
    assert knowledge_row(line).superseded_by == []


def test_the_ref_of_a_line_is_the_id_of_its_item_and_its_place() -> None:
    assert line_ref("S-0001", 2) == "S-0001#2"


def test_the_text_of_no_superseding_line_is_empty() -> None:
    assert superseded_text([]) == ""


def test_the_text_of_two_superseding_lines_names_both_after_two_spaces() -> None:
    assert superseded_text(["S-0001#2", "S-0002#1"]) == "  (superseded by S-0001#2, S-0002#1)"
