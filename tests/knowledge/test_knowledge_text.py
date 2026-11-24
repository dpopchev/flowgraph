"""The text of fgraph knowledge lists the mark of a line right after its text."""

from datetime import UTC, datetime

import pytest

from flowgraph.knowledge import KnowledgeRow
from flowgraph.knowledge.list import KnowledgeEntry, entries_of, knowledge_text

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_an_entry_marked_open_is_listed_with_its_mark_before_its_terms() -> None:
    entry = KnowledgeEntry("S-0001", "finding", NOW, "a text", ["gate"], mark="open")
    assert knowledge_text([entry], None, None) == (
        "2026-01-01  finding  S-0001  a text  (open)  (about gate)\n"
    )


def test_an_entry_with_no_mark_is_listed_as_before() -> None:
    entry = KnowledgeEntry("S-0001", "finding", NOW, "a text", ["gate"])
    assert knowledge_text([entry], None, None) == (
        "2026-01-01  finding  S-0001  a text  (about gate)\n"
    )


def test_the_entry_of_a_row_marked_open_holds_the_mark() -> None:
    row = KnowledgeRow("finding", NOW, "a text", mark="open")
    assert entries_of("S-0001", [row])[0].mark == "open"
