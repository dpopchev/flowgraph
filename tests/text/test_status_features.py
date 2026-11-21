"""The text of status with Features: a block of their own above the buckets."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.text import status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
ROWS = [WorkItemRow("ST-0001", "a title", "started", parent="F-0001", created=CREATED)]
FEATURES = [
    FeatureRow("F-0001", "a feature title", "InProgress"),
    FeatureRow("F-0002", "another feature title", "Backlog"),
]


def test_the_features_are_listed_above_the_buckets_each_with_its_bucket() -> None:
    assert status_text(ROWS, FEATURES) == (
        "Features (2)\n"
        "  F-0001  a feature title  InProgress\n"
        "  F-0002  another feature title  Backlog\n"
        "Backlog (0)\n"
        "InProgress (1)\n"
        "  ST-0001  a title\n"
        "Completed (0)\n"
    )


def test_no_heading_is_listed_for_the_features_when_there_is_none() -> None:
    assert status_text(ROWS, []).splitlines()[0] == "Backlog (0)"
