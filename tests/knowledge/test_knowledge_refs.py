"""The list of fgraph knowledge names each line by its ref and reads which lines supersede which."""

from datetime import UTC, datetime

import pytest

from flowgraph.knowledge import KnowledgeRow
from flowgraph.knowledge.list import (
    KnowledgeEntry,
    decision_entries,
    entries_of,
    knowledge_text,
    superseded_by,
)
from flowgraph.work_item import WorkItemDetail

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)
FIRST = KnowledgeRow("decision", NOW, "keep one store")
SECOND = KnowledgeRow("decision", NOW, "keep one file per item", supersedes=["S-0001#1"])


def naming(ref: str, *refs: str) -> KnowledgeEntry:
    """An entry under that ref that supersedes the lines of the refs given."""
    return KnowledgeEntry("S-0001", "decision", NOW, "a text", ref=ref, supersedes=list(refs))


def test_the_entries_of_an_item_carry_the_refs_of_their_places_from_one() -> None:
    assert [entry.ref for entry in entries_of("S-0001", [FIRST, SECOND])] == [
        "S-0001#1",
        "S-0001#2",
    ]


def test_an_entry_carries_the_refs_its_row_supersedes() -> None:
    assert entries_of("S-0001", [FIRST, SECOND])[1].supersedes == ["S-0001#1"]


def test_the_decision_of_a_completed_spike_has_no_ref() -> None:
    detail = WorkItemDetail(
        "Q-0001", "a title", "Completed", "", [], decision="one file", answer="yes"
    )
    assert decision_entries(detail, NOW)[0].ref == ""


def test_knowledge_text_writes_the_ref_in_the_column_of_the_item() -> None:
    assert knowledge_text([naming("S-0001#2")], None, None) == (
        "2026-01-01  decision  S-0001#2  a text\n"
    )


def test_knowledge_text_writes_the_item_of_an_entry_with_no_ref() -> None:
    entry = KnowledgeEntry("Q-0001", "decision", NOW, "one file")
    assert knowledge_text([entry], None, None) == "2026-01-01  decision  Q-0001  one file\n"


def test_no_entry_supersedes_no_line() -> None:
    assert superseded_by([]) == {}


def test_a_line_one_entry_names_is_superseded_by_that_entry() -> None:
    assert superseded_by([naming("S-0001#2", "S-0001#1")]) == {"S-0001#1": ["S-0001#2"]}


def test_a_line_two_entries_name_is_superseded_by_both_in_the_order_given() -> None:
    entries = [naming("S-0001#2", "S-0001#1"), naming("S-0002#1", "S-0001#1")]
    assert superseded_by(entries) == {"S-0001#1": ["S-0001#2", "S-0002#1"]}
