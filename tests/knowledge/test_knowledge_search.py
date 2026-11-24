"""The search of the knowledge list: the entries whose text holds a text, and the line it says."""

from datetime import UTC, datetime, timedelta

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.knowledge.list import (
    KnowledgeEntry,
    holding,
    knowledge_text,
    newest_first,
    sought,
)

pytestmark = pytest.mark.view

ON = datetime(2026, 1, 1, tzinfo=UTC)


def entry(
    text: str,
    item: str = "S-0001",
    kind: str = "finding",
    noted: datetime = ON,
    about: tuple[str, ...] = (),
    governs: tuple[str, ...] = (),
) -> KnowledgeEntry:
    return KnowledgeEntry(item, kind, noted, text, list(about), list(governs))


def test_holding_of_no_text_is_every_entry_in_the_order_given() -> None:
    entries = [entry("keep one store"), entry("a text"), entry("the Store is plain")]
    assert holding(entries, None) == entries


def test_holding_keeps_the_entries_whose_text_holds_the_text_in_the_order_given() -> None:
    entries = [entry("keep one store"), entry("a text"), entry("the Store is plain")]
    assert holding(entries, "store") == [entries[0], entries[2]]


@pytest.mark.parametrize(
    ("text", "search"),
    [("keep one store", "STORE"), ("the Store is plain", "store")],
)
def test_holding_keeps_an_entry_whose_text_holds_the_search_whatever_the_case(
    text: str, search: str
) -> None:
    assert holding([entry(text)], search) == [entry(text)]


@pytest.mark.parametrize("search", ["store", "S-0001", "decision"])
def test_holding_keeps_no_entry_for_a_search_of_its_terms_its_item_or_its_kind(
    search: str,
) -> None:
    kept = entry(
        "a text", item="S-0001", kind="decision", about=("store",), governs=("src/store.py",)
    )
    assert holding([kept], search) == []


def test_newest_first_of_the_entries_holding_a_text_is_the_newest_first() -> None:
    old = entry("a old text")
    new = entry("a new text", noted=ON + timedelta(days=1))
    assert newest_first(holding([old, new], "a"), None) == [new, old]


def test_sought_of_no_text_is_no_search() -> None:
    assert sought(None) is None


def test_sought_of_a_text_is_the_text_as_given() -> None:
    assert sought("one store") == "one store"


def test_sought_of_a_blank_text_is_refused_naming_the_search() -> None:
    with pytest.raises(EmptyPartError, match=r"^search is empty$"):
        sought(" ")


def test_knowledge_text_of_no_entry_and_a_search_names_the_search() -> None:
    assert knowledge_text([], None, None, "zzz") == (
        "no knowledge lines holding 'zzz' in the record\n"
    )


def test_knowledge_text_of_no_entry_with_a_kind_and_a_term_names_all_three() -> None:
    assert knowledge_text([], "decision", "gate", "zzz") == (
        "no decision lines about gate holding 'zzz' in the record\n"
    )


def test_knowledge_text_of_no_entry_and_no_search_is_as_before() -> None:
    assert knowledge_text([], None, None) == "no knowledge lines in the record\n"


def test_knowledge_text_of_one_entry_with_a_search_is_the_line_of_that_entry_alone() -> None:
    assert knowledge_text([entry("keep one store")], None, None, "store") == (
        "2026-01-01  finding  S-0001  keep one store\n"
    )
