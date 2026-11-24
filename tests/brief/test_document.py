"""The JSON document of a brief: the keys of its contract, null for nothing, the same bytes."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from flowgraph.brief.document import BriefFormatError, brief_json, chosen_brief_format
from flowgraph.brief.model import Brief, FeatureBrief, TermLine
from flowgraph.knowledge.list import KnowledgeEntry
from flowgraph.knowledge.model import KnowledgeRow
from flowgraph.task.model import TaskRow
from flowgraph.work_item.views import DependsRow, WorkItemDetail

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)
TASK = TaskRow("T-0002", "a task", "changed: src/gate.py", "", "started", check="make test")
STORY = WorkItemDetail(
    "S-0002",
    "a title",
    "started",
    "a description",
    [TASK],
    given="a",
    when="b",
    then="c",
    agent="sonnet-a1",
    parent="F-0001",
    complexity="medium",
    knowledge=[KnowledgeRow("decision", NOW, "read once", ["gate"], ["src/gate.py"])],
    depends_on=[DependsRow("S-0001", "completed"), DependsRow("S-0004", "in-progress")],
)
FEATURE = FeatureBrief(
    "F-0001", "in-progress", "a feature", "", (KnowledgeRow("decision", NOW, "one gate"),)
)
GOVERNING = KnowledgeEntry("S-0001", "decision", NOW, "no state", ["gate"], ["src/gate.py"])
STARTED = Brief(
    STORY,
    "wi/S-0002-a",
    Path("/w/S-0002-a"),
    FEATURE,
    (GOVERNING,),
    (TermLine("gate", "a check"),),
)
BARE = Brief(
    WorkItemDetail("S-0003", "a bare one", "backlog", "", [], given="a", when="b", then="c"),
    None,
    None,
    None,
    (),
    (),
)
BUG = Brief(
    WorkItemDetail("B-0001", "a bug", "backlog", "", [], observed="it fails", expected="it holds"),
    None,
    None,
    None,
    (),
    (),
)
SPIKE = Brief(
    WorkItemDetail(
        "Q-0001",
        "a question",
        "completed",
        "",
        [],
        hypothesis="is it?",
        decision="yes",
        answer="yes",
    ),
    None,
    None,
    None,
    (),
    (),
)


def parsed(brief: Brief) -> Any:
    return json.loads(brief_json(brief))


def test_the_top_level_keys_are_the_contract() -> None:
    assert list(parsed(STARTED)) == [
        "agent",
        "branch",
        "bucket",
        "complexity",
        "criterion",
        "depends_on",
        "description",
        "feature",
        "governed_by",
        "id",
        "kind",
        "knowledge",
        "state",
        "tasks",
        "terms",
        "title",
        "waits_for",
        "worktree",
    ]


def test_the_text_is_sorted_with_an_indent_of_two_and_ends_with_a_newline() -> None:
    printed = brief_json(STARTED)
    assert printed == json.dumps(json.loads(printed), indent=2, sort_keys=True) + "\n"


def test_two_calls_print_the_same_bytes() -> None:
    assert brief_json(STARTED) == brief_json(STARTED)


def test_the_kind_is_read_from_the_prefix_of_the_id() -> None:
    assert parsed(STARTED)["kind"] == "story"


def test_the_bucket_is_the_one_the_state_is_listed_in() -> None:
    assert parsed(STARTED)["bucket"] == "in-progress"


def test_the_branch_and_the_worktree_are_given_as_text() -> None:
    assert (parsed(STARTED)["branch"], parsed(STARTED)["worktree"]) == (
        "wi/S-0002-a",
        "/w/S-0002-a",
    )


def test_each_work_item_it_depends_on_holds_its_id_and_bucket() -> None:
    assert parsed(STARTED)["depends_on"] == [
        {"bucket": "completed", "id": "S-0001"},
        {"bucket": "in-progress", "id": "S-0004"},
    ]


def test_it_waits_for_the_work_items_it_depends_on_that_are_not_completed() -> None:
    assert parsed(STARTED)["waits_for"] == ["S-0004"]


def test_the_criterion_of_a_story_holds_its_given_when_then_and_null_for_the_rest() -> None:
    assert parsed(STARTED)["criterion"] == {
        "answer": None,
        "decision": None,
        "expected": None,
        "given": "a",
        "hypothesis": None,
        "observed": None,
        "then": "c",
        "when": "b",
    }


def test_the_criterion_of_a_bug_holds_what_is_observed_and_expected() -> None:
    criterion = parsed(BUG)["criterion"]
    assert (criterion["observed"], criterion["expected"], criterion["given"]) == (
        "it fails",
        "it holds",
        None,
    )


def test_the_criterion_of_a_spike_holds_its_hypothesis_decision_and_answer() -> None:
    criterion = parsed(SPIKE)["criterion"]
    assert (criterion["hypothesis"], criterion["decision"], criterion["answer"]) == (
        "is it?",
        "yes",
        "yes",
    )


def test_a_task_holds_its_parts_and_null_for_the_empty_ones() -> None:
    assert parsed(STARTED)["tasks"] == [
        {
            "check": "make test",
            "commit": None,
            "description": None,
            "expected_output": "changed: src/gate.py",
            "id": "T-0002",
            "reason": None,
            "state": "started",
            "title": "a task",
            "waiting_on": None,
        }
    ]


def test_the_feature_holds_its_parts_and_its_knowledge() -> None:
    assert parsed(STARTED)["feature"] == {
        "bucket": "in-progress",
        "description": None,
        "id": "F-0001",
        "knowledge": [
            {
                "about": [],
                "governs": [],
                "kind": "decision",
                "noted": "2026-01-01T12:30:00+00:00",
                "text": "one gate",
            }
        ],
        "title": "a feature",
    }


def test_a_line_that_governs_holds_its_item_kind_day_text_terms_and_files() -> None:
    assert parsed(STARTED)["governed_by"] == [
        {
            "about": ["gate"],
            "governs": ["src/gate.py"],
            "item": "S-0001",
            "kind": "decision",
            "noted": "2026-01-01T12:30:00+00:00",
            "text": "no state",
        }
    ]


def test_the_knowledge_of_the_work_item_itself_is_listed() -> None:
    assert [line["text"] for line in parsed(STARTED)["knowledge"]] == ["read once"]


def test_each_term_holds_its_name_and_meaning() -> None:
    assert parsed(STARTED)["terms"] == [{"meaning": "a check", "name": "gate"}]


@pytest.mark.parametrize("key", ["branch", "worktree", "feature", "agent", "complexity"])
def test_a_part_a_brief_holds_nothing_of_is_null(key: str) -> None:
    assert parsed(BARE)[key] is None


@pytest.mark.parametrize("key", ["depends_on", "waits_for", "governed_by", "terms", "tasks"])
def test_a_list_a_brief_holds_nothing_in_is_empty(key: str) -> None:
    assert parsed(BARE)[key] == []


def test_a_format_that_is_neither_is_refused_naming_the_word_and_both() -> None:
    with pytest.raises(BriefFormatError, match="--format 'xml' is not text or json"):
        chosen_brief_format("xml")
