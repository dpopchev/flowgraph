"""The text of the links of an item, a term and a file: each heading that holds a line."""

from datetime import UTC, datetime

import pytest

from flowgraph.about.links import (
    FileLinks,
    ItemLinks,
    Linked,
    Reached,
    ReachedLine,
    TermLinks,
    TouchedTask,
    Touching,
)
from flowgraph.about.text import file_text, item_text, term_about_text
from flowgraph.brief.model import TermLine
from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.knowledge.model import KnowledgeRow

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ENTRY = KnowledgeEntry("S-0001", "decision", NOW, "no state", governs=["src/gate.py"])
ITEM = ItemLinks(
    "S-0002",
    "a title",
    {"feature": [Linked("F-0001", "in-progress", "a feature")], "depends on": []},
    [TermLine("gate", "a check")],
    [KnowledgeRow("decision", NOW, "one gate", ["gate"], ["src/gate.py"])],
)
BARE_ITEM = ItemLinks("S-0002", "a title", {"feature": [], "depends on": []}, [], [])
TERM = TermLinks(
    "gate",
    "a check",
    NOW,
    (),
    (),
    [],
    [],
    [Reached("S-0001", ""), Reached("S-0002", "lane")],
    [ReachedLine(KnowledgeEntry("S-0002", "finding", NOW, "a find"), "lane")],
)
BARE_TERM = TermLinks("gate", "a check", NOW, (), (), [], [])
FILE = FileLinks(
    "work.txt",
    [ENTRY],
    [Touching("S-0001", "", "a title", [TouchedTask("T-0001", "abc1234", "a task")])],
)
BARE_FILE = FileLinks("work.txt", [], [])


def test_an_item_is_its_id_and_title_then_each_heading_that_holds_a_line() -> None:
    assert item_text(ITEM) == (
        "S-0002  a title\n"
        "  feature (1)\n"
        "    F-0001  in-progress  a feature\n"
        "  terms (1)\n"
        "    gate  a check\n"
        "  knowledge (1)\n"
        "    decision  2026-01-01  one gate  (about gate)  (governs src/gate.py)\n"
    )


def test_an_item_with_no_line_is_its_id_and_title() -> None:
    assert item_text(BARE_ITEM) == "S-0002  a title\n"


def test_a_term_lists_its_items_with_the_term_each_was_reached_through() -> None:
    assert term_about_text(TERM).startswith("  items  S-0001, S-0002  (via lane)\n  knowledge\n")


def test_a_term_lists_its_knowledge_lines_with_the_term_they_were_reached_through() -> None:
    assert term_about_text(TERM).endswith("    S-0002  finding  2026-01-01  a find  (via lane)\n")


def test_a_term_with_neither_is_the_empty_text() -> None:
    assert term_about_text(BARE_TERM) == ""


def test_a_file_lists_the_lines_that_govern_it_then_the_items_that_touched_it() -> None:
    assert file_text(FILE) == (
        "Governed by\n"
        "  decision  2026-01-01  S-0001  no state\n"
        "S-0001  -  a title\n"
        "  T-0001  abc1234  a task\n"
    )


def test_a_file_with_neither_is_said_in_one_line() -> None:
    assert file_text(BARE_FILE) == "no commit of the record touched work.txt\n"
