"""The JSON documents of fgraph show of a work item and of a Feature: the keys of their contract."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.feature import FeatureDetail
from flowgraph.knowledge import KnowledgeRow
from flowgraph.status.show_document import (
    ShowFormatError,
    chosen_show_format,
    feature_json,
    work_item_json,
)
from flowgraph.task.model import TaskRow
from flowgraph.work_item import ProgressRow, WorkItemRow
from flowgraph.work_item.views import DependsRow, VerifiedRow, WorkItemDetail

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)
STARTED_TASK = TaskRow("T-0002", "a task", "changed: src/gate.py", "", "started", check="make test")
BACKLOG_TASK = TaskRow("T-0003", "another task", "an output", "", "backlog")
STORY = WorkItemDetail(
    "S-0002",
    "a title",
    "started",
    "a description",
    [STARTED_TASK, BACKLOG_TASK],
    given="a",
    when="b",
    then="c",
    agent="sonnet-a1",
    parent="F-0001",
    realizes=2,
    realized="a criterion",
    complexity="medium",
    about=["gate"],
    knowledge=[
        KnowledgeRow(
            "finding", NOW, "read once", ["gate"], ["src/gate.py"], "open", [], ["S-0002#2"]
        ),
        KnowledgeRow("finding", NOW, "no mark"),
    ],
    depends_on=[DependsRow("S-0001", "completed")],
    progress=[ProgressRow(NOW, "the story moves"), ProgressRow(NOW, "the task moves", "T-0002")],
)
BARE = WorkItemDetail("S-0003", "a bare one", "backlog", "", [], given="a", when="b", then="c")
BUG = WorkItemDetail(
    "B-0001",
    "a bug",
    "blocked",
    "",
    [],
    observed="it fails",
    expected="it holds",
    reason="a reason",
    waiting_on="developer",
)
SPIKE = WorkItemDetail(
    "Q-0001",
    "a question",
    "completed",
    "",
    [],
    hypothesis="is it?",
    decision="yes",
    answer="yes",
    verified=VerifiedRow("yes", "it holds", NOW),
)
FEATURE = FeatureDetail("F-0001", "a feature", "", ["one", "two"], about=["gate"])
ROWS = [
    WorkItemRow("S-0001", "a", "completed", parent="F-0001", realizes=1, created=NOW),
    WorkItemRow("S-0002", "b", "backlog", parent="F-0001", created=NOW),
]
BLOCKED_FEATURE = FeatureDetail(
    "F-0002", "a blocked one", "", ["one"], reason="a reason", waiting_on="developer"
)
BARE_FEATURE = FeatureDetail("F-0003", "a bare one", "", ["one"])


def story() -> dict[str, Any]:
    return json.loads(work_item_json(STORY))


def bare() -> dict[str, Any]:
    return json.loads(work_item_json(BARE))


def feature() -> dict[str, Any]:
    return json.loads(feature_json(FEATURE, ROWS, "in-progress"))


def bare_feature() -> dict[str, Any]:
    return json.loads(feature_json(BARE_FEATURE, [], "backlog"))


def test_the_top_level_keys_of_a_work_item_are_the_contract() -> None:
    assert list(story()) == [
        "about",
        "agent",
        "amended_by",
        "amends",
        "bucket",
        "commit",
        "complexity",
        "criterion",
        "depends_on",
        "description",
        "filed_during",
        "filed_here",
        "id",
        "kind",
        "knowledge",
        "parent",
        "progress",
        "realized",
        "realizes",
        "reason",
        "state",
        "superseded_by",
        "supersedes",
        "tasks",
        "title",
        "verified",
        "waiting_on",
    ]


def test_the_text_of_a_work_item_is_canonical() -> None:
    printed = work_item_json(STORY)
    assert printed == json.dumps(json.loads(printed), indent=2, sort_keys=True) + "\n"


def test_two_calls_on_a_work_item_print_the_same_bytes() -> None:
    assert work_item_json(STORY) == work_item_json(STORY)


@pytest.mark.parametrize(
    ("detail", "kind"),
    [(STORY, "story"), (BUG, "bug"), (SPIKE, "spike")],
)
def test_the_kind_is_read_from_the_prefix_of_the_id(detail: WorkItemDetail, kind: str) -> None:
    assert json.loads(work_item_json(detail))["kind"] == kind


def test_the_bucket_of_a_started_story_is_in_progress() -> None:
    assert story()["bucket"] == "in-progress"


@pytest.mark.parametrize(("key", "value"), [("state", "blocked"), ("reason", "a reason")])
def test_a_blocked_bug_holds_its_state_and_its_reason(key: str, value: str) -> None:
    assert json.loads(work_item_json(BUG))[key] == value


def test_a_blocked_bug_holds_what_it_waits_on() -> None:
    assert json.loads(work_item_json(BUG))["waiting_on"] == "developer"


def test_the_criterion_of_a_story_holds_its_three_parts_and_null_for_the_others() -> None:
    assert story()["criterion"] == {
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
    criterion = json.loads(work_item_json(BUG))["criterion"]
    assert (criterion["observed"], criterion["expected"]) == ("it fails", "it holds")


def test_a_spike_holds_its_hypothesis_its_decision_and_its_answer() -> None:
    criterion = json.loads(work_item_json(SPIKE))["criterion"]
    assert (criterion["hypothesis"], criterion["decision"], criterion["answer"]) == (
        "is it?",
        "yes",
        "yes",
    )


def test_a_spike_holds_how_it_was_verified() -> None:
    assert json.loads(work_item_json(SPIKE))["verified"] == {
        "answer": "yes",
        "on": "2026-01-01T12:30:00+00:00",
        "text": "it holds",
    }


@pytest.mark.parametrize(("place", "bucket"), [(0, "in-progress"), (1, "backlog")])
def test_a_task_holds_its_bucket(place: int, bucket: str) -> None:
    assert story()["tasks"][place]["bucket"] == bucket


def test_a_task_holds_its_check() -> None:
    assert story()["tasks"][0]["check"] == "make test"


def test_a_task_holds_its_own_progress_lines() -> None:
    assert story()["tasks"][0]["progress"] == [
        {"noted": "2026-01-01T12:30:00+00:00", "text": "the task moves"}
    ]


def test_the_progress_of_a_story_holds_its_own_line_alone() -> None:
    assert story()["progress"] == [
        {"noted": "2026-01-01T12:30:00+00:00", "text": "the story moves"}
    ]


def test_a_knowledge_row_holds_its_mark() -> None:
    assert story()["knowledge"][0]["mark"] == "open"


def test_a_knowledge_row_holds_the_refs_that_supersede_it() -> None:
    assert story()["knowledge"][0]["superseded_by"] == ["S-0002#2"]


def test_an_unmarked_knowledge_row_holds_a_null_mark() -> None:
    assert story()["knowledge"][1]["mark"] is None


def test_it_depends_on_the_work_items_with_their_buckets() -> None:
    assert story()["depends_on"] == [{"bucket": "completed", "id": "S-0001"}]


def test_a_story_holds_the_criterion_it_realizes() -> None:
    assert (story()["realizes"], story()["realized"]) == (2, "a criterion")


@pytest.mark.parametrize(
    "key",
    [
        "agent",
        "amends",
        "commit",
        "complexity",
        "description",
        "filed_during",
        "parent",
        "realized",
        "realizes",
        "reason",
        "superseded_by",
        "verified",
        "waiting_on",
    ],
)
def test_a_bare_story_holds_null_for_what_it_has_not(key: str) -> None:
    assert bare()[key] is None


@pytest.mark.parametrize(
    "key",
    [
        "about",
        "amended_by",
        "depends_on",
        "filed_here",
        "knowledge",
        "progress",
        "supersedes",
        "tasks",
    ],
)
def test_a_bare_story_holds_an_empty_list_for_what_it_has_not(key: str) -> None:
    assert bare()[key] == []


def test_the_top_level_keys_of_a_feature_are_the_contract() -> None:
    assert list(feature()) == [
        "about",
        "bucket",
        "commit",
        "criteria",
        "description",
        "id",
        "kind",
        "knowledge",
        "reason",
        "title",
        "waiting_on",
        "work_items",
    ]


def test_a_feature_is_of_the_kind_feature() -> None:
    assert feature()["kind"] == "feature"


def test_a_feature_holds_the_bucket_it_is_given() -> None:
    assert feature()["bucket"] == "in-progress"


def test_the_criteria_of_a_feature_hold_who_realizes_them_and_whether_they_are_met() -> None:
    assert feature()["criteria"] == [
        {"met": True, "number": 1, "realized_by": ["S-0001"], "text": "one"},
        {"met": False, "number": 2, "realized_by": [], "text": "two"},
    ]


def test_the_work_items_of_a_feature_hold_their_buckets() -> None:
    assert feature()["work_items"] == [
        {"bucket": "completed", "id": "S-0001", "title": "a"},
        {"bucket": "backlog", "id": "S-0002", "title": "b"},
    ]


@pytest.mark.parametrize(("key", "value"), [("reason", "a reason"), ("waiting_on", "developer")])
def test_a_blocked_feature_holds_its_reason_and_what_it_waits_on(key: str, value: str) -> None:
    assert json.loads(feature_json(BLOCKED_FEATURE, [], "in-progress"))[key] == value


@pytest.mark.parametrize("key", ["commit", "description", "reason", "waiting_on"])
def test_a_bare_feature_holds_null_for_what_it_has_not(key: str) -> None:
    assert bare_feature()[key] is None


def test_the_text_of_a_feature_is_canonical() -> None:
    printed = feature_json(FEATURE, ROWS, "in-progress")
    assert printed == json.dumps(json.loads(printed), indent=2, sort_keys=True) + "\n"


def test_two_calls_on_a_feature_print_the_same_bytes() -> None:
    assert feature_json(FEATURE, ROWS, "backlog") == feature_json(FEATURE, ROWS, "backlog")


@pytest.mark.parametrize("format_", ["text", "json"])
def test_a_format_of_show_is_returned(format_: str) -> None:
    assert chosen_show_format(format_) == format_


def test_a_format_that_is_neither_is_refused_naming_both() -> None:
    with pytest.raises(
        ShowFormatError, match="--format 'xml' is not text or json, the two formats of show"
    ):
        chosen_show_format("xml")
