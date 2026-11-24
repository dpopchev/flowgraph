"""The JSON document of status holds the agent of a work item, the name or null."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status.document import status_json
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def story(**more: Any) -> WorkItemRow:
    """A Story started, with the parts given."""
    return WorkItemRow("S-0001", "a title", "started", created=CREATED, **more)


def only(row: WorkItemRow | FeatureRow) -> dict[str, Any]:
    """The one item of the document of the row, whatever its bucket."""
    buckets = json.loads(status_json([row]))["buckets"]
    return next(item for each in buckets for item in each["items"])


def test_a_work_item_holds_its_agent_as_the_name() -> None:
    assert only(story(agent="sonnet-a1"))["agent"] == "sonnet-a1"


def test_a_work_item_without_an_agent_holds_null() -> None:
    assert only(story())["agent"] is None


def test_a_work_item_of_a_feature_holds_its_agent_in_the_work_items() -> None:
    feature = FeatureRow(
        "F-0001", "a feature", "in-progress", 0, 1, work_items=[story(agent="sonnet-a1")]
    )
    assert only(feature)["work_items"][0]["agent"] == "sonnet-a1"
