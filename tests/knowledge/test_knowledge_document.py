"""The JSON document of the knowledge lines: its keys, null for nothing, the same bytes."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.knowledge.document import (
    KnowledgeFormatError,
    chosen_knowledge_format,
    knowledge_json,
)
from flowgraph.knowledge.list import KnowledgeEntry

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)
GOVERNING = KnowledgeEntry(
    "S-0001",
    "decision",
    NOW,
    "keep one store",
    ["gate"],
    ["src/store.py"],
    "standing",
    "S-0001#2",
    ["S-0001#1"],
)
SPIKE = KnowledgeEntry("Q-0001", "decision", NOW, "one file (answer yes)")


def parsed(entries: list[KnowledgeEntry]) -> Any:
    return json.loads(knowledge_json(entries))


def test_the_document_holds_one_key_named_lines() -> None:
    assert list(parsed([GOVERNING])) == ["lines"]


def test_the_first_line_holds_every_field_of_the_entry() -> None:
    assert parsed([GOVERNING])["lines"][0] == {
        "about": ["gate"],
        "governs": ["src/store.py"],
        "item": "S-0001",
        "kind": "decision",
        "mark": "standing",
        "noted": "2026-01-01T12:30:00+00:00",
        "ref": "S-0001#2",
        "supersedes": ["S-0001#1"],
        "text": "keep one store",
    }


def test_the_line_of_a_spike_holds_a_null_ref() -> None:
    assert parsed([SPIKE])["lines"][0]["ref"] is None


def test_the_line_of_a_spike_holds_a_null_mark() -> None:
    assert parsed([SPIKE])["lines"][0]["mark"] is None


@pytest.mark.parametrize("key", ["about", "governs", "supersedes"])
def test_the_line_of_a_spike_holds_an_empty_list_for_each_list(key: str) -> None:
    assert parsed([SPIKE])["lines"][0][key] == []


def test_the_lines_keep_the_order_given() -> None:
    assert [line["item"] for line in parsed([SPIKE, GOVERNING])["lines"]] == [
        "Q-0001",
        "S-0001",
    ]


def test_no_entry_gives_an_empty_list_of_lines() -> None:
    assert parsed([]) == {"lines": []}


def test_the_text_is_sorted_with_an_indent_of_two_and_ends_with_a_newline() -> None:
    printed = knowledge_json([GOVERNING, SPIKE])
    assert printed == json.dumps(json.loads(printed), indent=2, sort_keys=True) + "\n"


def test_two_calls_print_the_same_bytes() -> None:
    assert knowledge_json([GOVERNING, SPIKE]) == knowledge_json([GOVERNING, SPIKE])


@pytest.mark.parametrize("format_", ["text", "json"])
def test_the_format_asked_for_is_chosen(format_: str) -> None:
    assert chosen_knowledge_format(format_) == format_


def test_a_format_that_is_neither_is_refused_naming_both_formats() -> None:
    with pytest.raises(KnowledgeFormatError, match="--format 'xml' is not text or json"):
        chosen_knowledge_format("xml")
