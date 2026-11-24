"""The text of status under the names of the buckets to list: the others are passed over."""

from datetime import UTC, datetime

import pytest

from flowgraph.status import status_text
from flowgraph.status.buckets import BACKLOG_BUCKET, REMOVED_BUCKET
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
BACKLOG = WorkItemRow("S-0001", "title 1", "backlog", created=CREATED)
REMOVED = WorkItemRow("S-0002", "title 2", "removed", created=CREATED, reason="not wanted")


def test_the_name_of_the_backlog_alone_lists_its_heading_and_its_lines() -> None:
    assert status_text([BACKLOG], buckets={BACKLOG_BUCKET}) == (
        "Backlog (1)\n  S-0001  []  title 1\n"
    )


def test_no_names_given_lists_every_heading() -> None:
    assert status_text([BACKLOG]).splitlines() == [
        "Backlog (1)",
        "  S-0001  []  title 1",
        "InProgress (0)",
        "Completed (0)",
    ]


def test_removed_named_and_empty_has_no_heading() -> None:
    assert "Removed (0)" not in status_text([BACKLOG], buckets={BACKLOG_BUCKET, REMOVED_BUCKET})


def test_removed_holding_a_row_and_not_named_has_no_heading() -> None:
    assert "Removed (1)" not in status_text([REMOVED], buckets={BACKLOG_BUCKET})
