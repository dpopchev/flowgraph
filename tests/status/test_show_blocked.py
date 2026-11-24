"""The text of fgraph show for a blocked work item: blocked in its bucket, its reason and who."""

import pytest

from flowgraph.status import show_text
from flowgraph.work_item import WorkItemDetail

pytestmark = pytest.mark.view


def test_a_blocked_work_item_is_shown_blocked_with_its_reason_and_what_it_waits_on() -> None:
    blocked = WorkItemDetail(
        "S-0001",
        "a title",
        "blocked",
        "",
        [],
        given="a state",
        when="an action",
        then="another",
        reason="no key",
        waiting_on="developer",
    )
    assert show_text(blocked).splitlines()[1:4] == [
        "  bucket       in-progress, blocked",
        "  reason       no key",
        "  waiting on   developer",
    ]


def test_a_started_work_item_is_shown_with_no_block() -> None:
    started = WorkItemDetail(
        "S-0001", "a title", "started", "", [], given="a state", when="an action", then="another"
    )
    assert show_text(started).splitlines()[1:3] == [
        "  bucket       in-progress",
        "  given        a state",
    ]
