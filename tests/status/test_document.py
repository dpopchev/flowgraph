"""The JSON document of status: the buckets with every item of them, the next to start apart."""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status.document import StatusFormatError, chosen_format, status_json
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def story(item: str, state: str = "backlog", **more: Any) -> WorkItemRow:
    """A Story in that state."""
    return WorkItemRow(item, "a title", state, created=CREATED, **more)


def task(item: str, state: str, **more: str) -> TaskRow:
    """A Task in that state."""
    return TaskRow(item, "a task", "an output", "", state, **more)


def feature(
    item: str = "F-0001", bucket: str = "Backlog", completed: int = 0, **more: Any
) -> FeatureRow:
    """A Feature in that bucket holding two work items, that many of them completed."""
    return FeatureRow(item, "a feature", bucket, completed, 2, **more)


def document(*rows: WorkItemRow | FeatureRow) -> dict[str, Any]:
    """The document of the rows, parsed."""
    return json.loads(status_json(rows))


def bucket(rows: Sequence[WorkItemRow | FeatureRow], name: str) -> dict[str, Any]:
    """The bucket of that name of the document of the rows."""
    return next(each for each in document(*rows)["buckets"] if each["name"] == name)


def only(row: WorkItemRow | FeatureRow) -> dict[str, Any]:
    """The one item of the document of the row, whatever its bucket."""
    return next(item for each in document(row)["buckets"] for item in each["items"])


def test_the_buckets_are_listed_in_the_order_of_the_flow() -> None:
    assert [each["name"] for each in document()["buckets"]] == [
        "Backlog",
        "InProgress",
        "Completed",
        "Removed",
    ]


def test_a_bucket_holding_nothing_is_listed_with_a_count_of_zero() -> None:
    assert bucket([], "Removed") == {"count": 0, "items": [], "name": "Removed"}


def test_each_bucket_holds_the_count_of_its_items() -> None:
    rows = [story("S-0001"), story("S-0002"), story("S-0003", "completed")]
    assert [(each["name"], each["count"]) for each in document(*rows)["buckets"]] == [
        ("Backlog", 2),
        ("InProgress", 0),
        ("Completed", 1),
        ("Removed", 0),
    ]


def test_a_bucket_lists_every_item_of_it_in_the_order_given() -> None:
    rows = [story(f"S-{number:04d}") for number in range(1, 9)]
    assert [item["id"] for item in bucket(rows, "Backlog")["items"]] == [row.id for row in rows]


def test_a_blocked_work_item_is_listed_under_inprogress() -> None:
    assert bucket([story("S-0001", "blocked")], "InProgress")["count"] == 1


def test_an_item_holds_its_id_its_title_and_its_state() -> None:
    item = only(story("S-0001"))
    assert (item["id"], item["title"], item["state"]) == ("S-0001", "a title", "backlog")


@pytest.mark.parametrize(
    ("item", "kind"),
    [("S-0001", "story"), ("U-0001", "upkeep"), ("B-0001", "bug"), ("Q-0001", "spike")],
)
def test_an_item_holds_its_kind_by_the_prefix_of_its_id(item: str, kind: str) -> None:
    assert only(story(item))["kind"] == kind


def test_a_work_item_holds_its_complexity_as_the_word() -> None:
    assert only(story("S-0001", complexity="high"))["complexity"] == "high"


def test_a_work_item_without_a_complexity_holds_null() -> None:
    assert only(story("S-0001"))["complexity"] is None


def test_a_feature_holds_the_kind_feature() -> None:
    assert only(feature())["kind"] == "feature"


def test_a_started_work_item_holds_its_progress_in_tasks() -> None:
    tasks = [task("T-0001", "completed"), task("T-0002", "started"), task("T-0003", "backlog")]
    assert only(story("S-0001", "started", tasks=tasks))["progress"] == {
        "completed": 1,
        "total": 3,
    }


def test_a_work_item_holds_each_of_its_tasks_with_its_state() -> None:
    tasks = [task("T-0001", "completed"), task("T-0002", "backlog")]
    held = only(story("S-0001", "started", tasks=tasks))["tasks"]
    assert [(each["id"], each["title"], each["state"]) for each in held] == [
        ("T-0001", "a task", "completed"),
        ("T-0002", "a task", "backlog"),
    ]


def test_a_blocked_task_holds_its_reason_and_what_it_waits_on() -> None:
    tasks = [task("T-0001", "blocked", reason="no key", waiting_on="the developer")]
    held = only(story("S-0001", "started", tasks=tasks))["tasks"][0]
    assert (held["reason"], held["waiting_on"]) == ("no key", "the developer")


def test_a_task_that_is_not_blocked_holds_no_reason_and_waits_on_nothing() -> None:
    held = only(story("S-0001", "started", tasks=[task("T-0001", "started")]))["tasks"][0]
    assert (held["reason"], held["waiting_on"]) == (None, None)


def test_a_completed_task_holds_its_commit() -> None:
    tasks = [task("T-0001", "completed", commit="abc1234")]
    assert only(story("S-0001", "started", tasks=tasks))["tasks"][0]["commit"] == "abc1234"


def test_a_completed_work_item_holds_its_commit() -> None:
    assert only(story("S-0001", "completed", commit="def5678"))["commit"] == "def5678"


def test_a_removed_work_item_holds_its_reason_and_the_one_that_supersedes_it() -> None:
    item = only(story("S-0001", "removed", reason="not wanted", superseded_by="S-0002"))
    assert (item["reason"], item["superseded_by"]) == ("not wanted", "S-0002")


def test_a_work_item_holds_the_ids_it_waits_for_in_the_order_given() -> None:
    assert only(story("S-0003", waits_for=["S-0002", "S-0001"]))["waits_for"] == [
        "S-0002",
        "S-0001",
    ]


def test_a_work_item_that_waits_for_nothing_holds_an_empty_list() -> None:
    assert only(story("S-0001"))["waits_for"] == []


def test_a_feature_holds_its_progress_in_work_items() -> None:
    assert only(feature(completed=1))["progress"] == {"completed": 1, "total": 2}


def test_a_feature_holds_the_ids_its_first_work_item_waits_for() -> None:
    assert only(feature(waits_for=["S-0009"]))["waits_for"] == ["S-0009"]


def test_a_feature_holds_every_work_item_under_it_with_its_state_in_the_order_given() -> None:
    held = [
        story("S-0003", "completed"),
        story("S-0004", "started", tasks=[task("T-0001", "started")]),
        story("S-0005", "backlog", waits_for=["S-0004"]),
        story("S-0006", "removed"),
    ]
    listed = only(feature(bucket="InProgress", work_items=held))["work_items"]
    assert [(each["id"], each["state"]) for each in listed] == [
        ("S-0003", "completed"),
        ("S-0004", "started"),
        ("S-0005", "backlog"),
        ("S-0006", "removed"),
    ]


def test_a_work_item_of_a_feature_holds_its_tasks_and_the_ids_it_waits_for() -> None:
    held = [story("S-0005", "backlog", waits_for=["S-0004"], tasks=[task("T-0001", "backlog")])]
    listed = only(feature(work_items=held))["work_items"][0]
    assert (listed["tasks"][0]["id"], listed["waits_for"]) == ("T-0001", ["S-0004"])


def test_a_blocked_feature_holds_its_reason_and_what_it_waits_on() -> None:
    blocked = feature(bucket="InProgress", waiting_on="the sponsor", block_reason="no budget")
    assert only(blocked)["block"] == {"reason": "no budget", "waiting_on": "the sponsor"}


def test_a_feature_that_is_not_blocked_holds_no_block() -> None:
    assert only(feature())["block"] is None


def test_a_removed_feature_holds_its_reason() -> None:
    assert only(feature(bucket="Removed", reason="not wanted"))["reason"] == "not wanted"


def test_the_next_to_start_is_the_id_of_the_line_marked() -> None:
    rows = [story("S-0001"), story("S-0002", next_to_start=True)]
    assert document(*rows)["next_to_start"] == "S-0002"


def test_the_next_to_start_is_a_feature_when_it_is_the_one_marked() -> None:
    assert document(feature(next_to_start=True))["next_to_start"] == "F-0001"


def test_the_next_to_start_is_null_when_no_line_is_marked() -> None:
    assert document(story("S-0001"))["next_to_start"] is None


def test_the_document_ends_with_a_newline() -> None:
    assert status_json([]).endswith("}\n")


def test_the_document_is_written_with_its_keys_sorted_and_an_indent_of_two() -> None:
    assert status_json([]).startswith('{\n  "buckets": [\n    {\n      "count": 0,')


def test_the_keys_of_an_item_are_sorted() -> None:
    item = only(story("S-0001"))
    assert list(item) == sorted(item)


def test_two_documents_of_the_same_rows_are_the_same_bytes() -> None:
    rows = [story("S-0001"), feature()]
    assert status_json(rows) == status_json(rows)


@pytest.mark.parametrize("format_", ["text", "json"])
def test_a_format_that_is_text_or_json_is_chosen(format_: str) -> None:
    assert chosen_format(format_) == format_


def test_a_format_that_is_none_is_refused_naming_it_and_the_two() -> None:
    with pytest.raises(StatusFormatError) as refused:
        chosen_format("xml")
    assert str(refused.value) == "--format 'xml' is not text or json, the two formats of status"
