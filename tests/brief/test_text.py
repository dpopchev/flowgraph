"""The text of the brief of a work item: the text of show, then each section that holds a line."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.brief.model import Brief, FeatureBrief, TermLine
from flowgraph.brief.text import brief_text
from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.knowledge.model import KnowledgeRow
from flowgraph.status.show import show_text
from flowgraph.work_item.views import WorkItemDetail

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)
DETAIL = WorkItemDetail("S-0002", "a title", "started", "", [], given="a", when="b", then="c")
BARE = Brief(DETAIL, None, None, None, (), ())
FEATURE = FeatureBrief(
    "F-0001",
    "in-progress",
    "a feature",
    "what it holds",
    (KnowledgeRow("decision", NOW, "one gate", ["gate"], ["src/gate.py"]),),
)
GOVERNING = KnowledgeEntry("S-0001", "decision", NOW, "no state", governs=["src/gate.py"])


def test_a_brief_with_nothing_beside_its_work_item_is_exactly_the_text_of_show() -> None:
    assert brief_text(BARE) == show_text(DETAIL)


def test_the_worktree_lists_the_branch_and_the_path() -> None:
    brief = Brief(DETAIL, "wi/S-0002-a", Path("/w/S-0002-a"), None, (), ())
    assert brief_text(brief).removeprefix(show_text(DETAIL)) == (
        "Worktree\n  branch       wi/S-0002-a\n  path         /w/S-0002-a\n"
    )


def test_a_branch_with_no_worktree_lists_the_branch_alone() -> None:
    brief = Brief(DETAIL, "wi/S-0002-a", None, None, (), ())
    assert brief_text(brief).removeprefix(show_text(DETAIL)) == (
        "Worktree\n  branch       wi/S-0002-a\n"
    )


def test_the_feature_lists_its_id_bucket_title_description_and_knowledge() -> None:
    brief = Brief(DETAIL, None, None, FEATURE, (), ())
    assert brief_text(brief).removeprefix(show_text(DETAIL)) == (
        "Feature\n"
        "  F-0001  in-progress  a feature\n"
        "  description  what it holds\n"
        "  Knowledge (1)\n"
        "    decision  2026-01-01  one gate  (about gate)  (governs src/gate.py)\n"
    )


def test_a_feature_with_no_description_and_no_knowledge_lists_its_line_alone() -> None:
    brief = Brief(
        DETAIL, None, None, FeatureBrief("F-0001", "backlog", "a feature", "", ()), (), ()
    )
    assert brief_text(brief).removeprefix(show_text(DETAIL)) == (
        "Feature\n  F-0001  backlog  a feature\n"
    )


def test_the_governing_lines_are_listed_under_governed_by() -> None:
    brief = Brief(DETAIL, None, None, None, (GOVERNING,), ())
    assert brief_text(brief).removeprefix(show_text(DETAIL)) == (
        "Governed by\n  decision  2026-01-01  S-0001  no state\n"
    )


def test_the_terms_are_listed_with_their_count_and_meaning() -> None:
    brief = Brief(DETAIL, None, None, None, (), (TermLine("gate", "a check"),))
    assert brief_text(brief).removeprefix(show_text(DETAIL)) == "Terms (1)\n  gate  a check\n"
