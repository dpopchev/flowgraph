"""The JSON document of the links of about: the keys of its contract, null for nothing."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.about.document import AboutFormatError, about_json, chosen_about_format
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
from flowgraph.brief.model import TermLine
from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.knowledge.model import KnowledgeRow

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)
HEADINGS = [
    "feature",
    "depends on",
    "depended on by",
    "filed during",
    "filed here",
    "supersedes",
    "superseded by",
    "amends",
    "amended by",
]
OTHERS = [heading.replace(" ", "_") for heading in HEADINGS[1:]]
ROW = KnowledgeRow("decision", NOW, "one gate", ["gate"], ["src/gate.py"])
ENTRY = KnowledgeEntry("S-0001", "decision", NOW, "no state", governs=["src/gate.py"])
ITEM = ItemLinks(
    "S-0002",
    "a title",
    {
        heading: [Linked("F-0001", "in-progress", "a feature")] if heading == "feature" else []
        for heading in HEADINGS
    },
    [TermLine("gate", "a check")],
    [ROW],
)
FEATURE = ItemLinks(
    "F-0001",
    "a feature",
    {"work items": [Linked("S-0002", "started", "a title")]},
    [],
    [],
)
TERM = TermLinks(
    "gate",
    "a check",
    NOW,
    ("check",),
    ("lane",),
    ["kind"],
    ["part"],
    [Reached("S-0001", ""), Reached("S-0002", "lane")],
    [ReachedLine(KnowledgeEntry("S-0002", "finding", NOW, "a find", ref="k1"), "lane")],
)
FILE = FileLinks(
    "work.txt",
    [ENTRY],
    [Touching("S-0001", "", "a title", [TouchedTask("T-0001", "abc1234", "a task")])],
)
BARE_FILE = FileLinks("work.txt", [], [])
DOCUMENTS = [ITEM, FEATURE, TERM, FILE]


def document(links: ItemLinks | TermLinks | FileLinks) -> Any:
    """The JSON of the links, parsed."""
    return json.loads(about_json(links))


def test_the_keys_of_a_work_item_are_its_parts_and_each_relation() -> None:
    assert list(document(ITEM)) == [
        "amended_by",
        "amends",
        "depended_on_by",
        "depends_on",
        "feature",
        "filed_during",
        "filed_here",
        "id",
        "kind",
        "knowledge",
        "superseded_by",
        "supersedes",
        "terms",
        "title",
    ]


@pytest.mark.parametrize(("id_", "kind"), [("S-0002", "story"), ("B-0002", "bug")])
def test_the_kind_of_a_work_item_is_the_noun_of_the_prefix(id_: str, kind: str) -> None:
    links = ItemLinks(id_, "a title", ITEM.links, [], [])
    assert document(links)["kind"] == kind


def test_the_feature_of_a_work_item_is_linked_with_its_bucket_and_title() -> None:
    assert document(ITEM)["feature"] == [
        {"bucket": "in-progress", "id": "F-0001", "title": "a feature"}
    ]


@pytest.mark.parametrize("relation", OTHERS)
def test_a_relation_with_nothing_is_an_empty_list(relation: str) -> None:
    assert document(ITEM)[relation] == []


def test_a_feature_holds_its_parts_and_its_work_items_alone() -> None:
    assert sorted(document(FEATURE)) == [
        "id",
        "kind",
        "knowledge",
        "terms",
        "title",
        "work_items",
    ]


def test_a_feature_is_of_the_kind_feature() -> None:
    assert document(FEATURE)["kind"] == "feature"


def test_a_feature_lists_each_work_item_with_its_bucket_and_title() -> None:
    assert document(FEATURE)["work_items"] == [
        {"bucket": "started", "id": "S-0002", "title": "a title"}
    ]


def test_a_term_line_is_its_name_and_its_meaning() -> None:
    assert document(ITEM)["terms"] == [{"meaning": "a check", "name": "gate"}]


def test_a_knowledge_row_holds_seven_keys() -> None:
    assert sorted(document(ITEM)["knowledge"][0]) == [
        "about",
        "governs",
        "kind",
        "mark",
        "noted",
        "supersedes",
        "text",
    ]


def test_the_mark_of_a_knowledge_row_with_none_is_null() -> None:
    assert document(ITEM)["knowledge"][0]["mark"] is None


def test_the_keys_of_a_term_are_its_head_and_what_is_about_it() -> None:
    assert list(document(TERM)) == [
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


def test_the_items_of_a_term_hold_the_term_each_was_reached_through() -> None:
    assert document(TERM)["items"] == [
        {"id": "S-0001", "via": None},
        {"id": "S-0002", "via": "lane"},
    ]


def test_a_line_of_a_term_holds_the_term_it_was_reached_through() -> None:
    assert document(TERM)["knowledge"][0]["via"] == "lane"


def test_a_line_of_a_term_holds_the_ref_of_its_entry() -> None:
    assert document(TERM)["knowledge"][0]["ref"] == "k1"


def test_a_term_was_added_at_the_full_iso_time() -> None:
    assert document(TERM)["added"] == "2026-01-01T00:00:00+00:00"


def test_a_file_holds_what_governs_it_and_what_touched_it_alone() -> None:
    assert sorted(document(FILE)) == ["governed_by", "kind", "path", "touched_by"]


def test_a_file_is_of_the_kind_file() -> None:
    assert document(FILE)["kind"] == "file"


def test_a_file_lists_the_item_that_touched_it_with_its_tasks() -> None:
    assert document(FILE)["touched_by"] == [
        {
            "commit": None,
            "id": "S-0001",
            "tasks": [{"commit": "abc1234", "id": "T-0001", "title": "a task"}],
            "title": "a title",
        }
    ]


@pytest.mark.parametrize("key", ["governed_by", "touched_by"])
def test_a_file_with_neither_holds_an_empty_list_for_each(key: str) -> None:
    assert document(BARE_FILE)[key] == []


@pytest.mark.parametrize("links", DOCUMENTS, ids=["item", "feature", "term", "file"])
def test_each_document_is_printed_with_sorted_keys_an_indent_of_two_and_a_newline(
    links: ItemLinks | TermLinks | FileLinks,
) -> None:
    printed = about_json(links)
    assert printed == json.dumps(json.loads(printed), indent=2, sort_keys=True) + "\n"


def test_two_calls_print_the_same_bytes() -> None:
    assert about_json(TERM) == about_json(TERM)


@pytest.mark.parametrize("format_", ["text", "json"])
def test_a_format_of_the_two_is_chosen(format_: str) -> None:
    assert chosen_about_format(format_) == format_


def test_a_format_that_is_neither_is_refused_naming_both() -> None:
    with pytest.raises(
        AboutFormatError, match="--format 'xml' is not text or json, the two formats of about"
    ):
        chosen_about_format("xml")
