"""The live lines of a record: those no later line supersedes, and the text for none of them."""

from datetime import UTC, datetime

import pytest

from flowgraph.knowledge.list import KnowledgeEntry, knowledge_text, live_entries

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def line(ref: str, supersedes: list[str] | None = None) -> KnowledgeEntry:
    """A finding of the item of the ref, under that ref, superseding the refs given."""
    return KnowledgeEntry(
        ref.partition("#")[0], "finding", NOW, "a text", ref=ref, supersedes=supersedes or []
    )


FIRST = line("S-0001#1")
SECOND = line("S-0001#2", ["S-0001#1"])
THIRD = line("S-0001#3", ["S-0001#2"])
NO_REF = KnowledgeEntry("Q-0001", "decision", NOW, "one file")


def test_with_no_supersede_every_entry_is_live_in_order() -> None:
    assert live_entries([FIRST, NO_REF]) == [FIRST, NO_REF]


def test_an_entry_another_names_is_left_out() -> None:
    assert live_entries([FIRST, SECOND]) == [SECOND]


def test_an_entry_named_by_a_named_entry_stays_out() -> None:
    assert live_entries([FIRST, SECOND, THIRD]) == [THIRD]


def test_an_entry_with_no_ref_is_kept_though_the_others_are_named() -> None:
    assert live_entries([FIRST, SECOND, NO_REF]) == [SECOND, NO_REF]


def test_an_entry_that_names_a_ref_no_entry_has_changes_nothing() -> None:
    assert live_entries([line("S-0001#1", ["S-0009#9"])]) == [line("S-0001#1", ["S-0009#9"])]


def test_live_text_of_no_entry_says_there_are_no_live_knowledge_lines() -> None:
    assert knowledge_text([], None, None, None, True) == ("no live knowledge lines in the record\n")


def test_live_text_of_no_entry_with_a_kind_and_a_term_names_all_three() -> None:
    assert knowledge_text([], "finding", "gate", None, True) == (
        "no live finding lines about gate in the record\n"
    )


def test_text_of_no_entry_without_live_is_as_before() -> None:
    assert knowledge_text([], None, None, None, False) == "no knowledge lines in the record\n"
