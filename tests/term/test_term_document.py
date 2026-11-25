"""The JSON document of a term: the keys of its contract, null for nothing, the same bytes."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.term.document import term_json
from flowgraph.term.item import TermShown

pytestmark = pytest.mark.view

ADDED = datetime(2026, 1, 1, tzinfo=UTC)
FIRST = KnowledgeEntry(
    "S-0001", "finding", ADDED, "a thing learned", ["gate"], ["src/gate.py"], "open", "S-0001#1", []
)
SECOND = KnowledgeEntry("Q-0001", "decision", ADDED, "one file (answer yes)")
SHOWN = TermShown(
    "gate",
    "a check",
    ADDED,
    ("check",),
    ("lane",),
    ("work-item",),
    ("part",),
    ("S-0001", "F-0001"),
    (FIRST, SECOND),
)
BARE = TermShown("gate", "a check", ADDED, (), (), (), ())


def shown() -> dict[str, Any]:
    return json.loads(term_json(SHOWN))


def test_the_top_level_keys_are_the_contract() -> None:
    assert list(shown()) == [
        "added",
        "is_a",
        "items",
        "kind",
        "kinds",
        "knowledge",
        "meaning",
        "name",
        "part_of",
        "parts",
    ]


def test_the_kind_is_term() -> None:
    assert shown()["kind"] == "term"


def test_the_day_added_is_the_full_iso_time() -> None:
    assert shown()["added"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("is_a", ["check"]),
        ("part_of", ["lane"]),
        ("kinds", ["work-item"]),
        ("parts", ["part"]),
        ("items", ["S-0001", "F-0001"]),
    ],
)
def test_a_relation_is_the_list_given(key: str, value: list[str]) -> None:
    assert shown()[key] == value


def test_the_first_knowledge_line_holds_all_its_parts() -> None:
    assert shown()["knowledge"][0] == {
        "about": ["gate"],
        "governs": ["src/gate.py"],
        "item": "S-0001",
        "kind": "finding",
        "mark": "open",
        "noted": "2026-01-01T00:00:00+00:00",
        "ref": "S-0001#1",
        "supersedes": [],
        "text": "a thing learned",
    }


def test_a_line_without_a_mark_holds_a_null_mark() -> None:
    assert shown()["knowledge"][1]["mark"] is None


def test_the_decision_of_a_spike_holds_a_null_ref() -> None:
    assert shown()["knowledge"][1]["ref"] is None


@pytest.mark.parametrize("key", ["is_a", "part_of", "kinds", "parts", "items", "knowledge"])
def test_a_bare_term_holds_an_empty_list_for_what_it_has_not(key: str) -> None:
    assert json.loads(term_json(BARE))[key] == []


def test_the_text_is_canonical() -> None:
    printed = term_json(SHOWN)
    assert printed == json.dumps(json.loads(printed), indent=2, sort_keys=True) + "\n"


def test_two_calls_print_the_same_bytes() -> None:
    assert term_json(SHOWN) == term_json(SHOWN)
