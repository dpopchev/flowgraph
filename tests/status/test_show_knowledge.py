"""The text of fgraph show lists the mark of a knowledge line right after its text."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureDetail
from flowgraph.knowledge import KnowledgeRow
from flowgraph.status import feature_text, show_text
from flowgraph.work_item import WorkItemDetail

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def shown(*rows: KnowledgeRow) -> str:
    """The text of show for a started work item that holds the rows."""
    return show_text(
        WorkItemDetail(
            "S-0001",
            "a title",
            "started",
            "",
            [],
            given="a state",
            when="an action",
            then="another",
            knowledge=list(rows),
        )
    )


def test_a_line_marked_open_ends_with_its_mark() -> None:
    assert shown(KnowledgeRow("finding", NOW, "a text", mark="open")).endswith(
        "Knowledge (1)\n  finding  2026-01-01  a text  (open)\n"
    )


def test_the_mark_comes_before_the_terms_and_the_files_of_the_line() -> None:
    row = KnowledgeRow("finding", NOW, "a text", ["gate"], ["src/gate.py"], "open")
    assert shown(row).endswith(
        "  finding  2026-01-01  a text  (open)  (about gate)  (governs src/gate.py)\n"
    )


def test_a_line_with_no_mark_ends_with_its_text() -> None:
    assert shown(KnowledgeRow("finding", NOW, "a text")).endswith("  finding  2026-01-01  a text\n")


def test_a_decision_of_a_feature_marked_standing_ends_with_its_mark() -> None:
    detail = FeatureDetail(
        "F-0001",
        "a feature title",
        "",
        ["a criterion"],
        knowledge=[KnowledgeRow("decision", NOW, "a text", mark="standing")],
    )
    assert feature_text(detail, [], "backlog").endswith(
        "  decision  2026-01-01  a text  (standing)\n"
    )


def test_a_superseded_line_ends_with_the_ref_of_the_line_that_supersedes_it() -> None:
    row = KnowledgeRow("decision", NOW, "a text", superseded_by=["S-0001#2"])
    assert shown(row).endswith("  decision  2026-01-01  a text  (superseded by S-0001#2)\n")


def test_the_refs_that_supersede_a_line_come_after_its_mark_terms_and_files() -> None:
    row = KnowledgeRow(
        "finding", NOW, "a text", ["gate"], ["src/gate.py"], "open", superseded_by=["S-0001#2"]
    )
    assert shown(row).endswith(
        "  finding  2026-01-01  a text  (open)  (about gate)  (governs src/gate.py)"
        "  (superseded by S-0001#2)\n"
    )


def test_two_refs_that_supersede_a_line_are_joined_by_a_comma() -> None:
    row = KnowledgeRow("decision", NOW, "a text", superseded_by=["S-0001#2", "S-0002#1"])
    assert shown(row).endswith("  a text  (superseded by S-0001#2, S-0002#1)\n")


def test_a_superseded_line_of_a_feature_ends_with_the_refs_that_supersede_it() -> None:
    detail = FeatureDetail(
        "F-0001",
        "a feature title",
        "",
        ["a criterion"],
        knowledge=[KnowledgeRow("decision", NOW, "a text", superseded_by=["F-0001#2"])],
    )
    assert feature_text(detail, [], "backlog").endswith(
        "  decision  2026-01-01  a text  (superseded by F-0001#2)\n"
    )
