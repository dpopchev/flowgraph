"""The text of a work item removed as superseded: its line in status and its show, both sides."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.status import show_text, status_text
from flowgraph.work_item import WorkItemDetail, WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def removed(reason: str) -> WorkItemRow:
    """A removed work item superseded by S-0002, with the reason given."""
    return WorkItemRow(
        "S-0001", "a title", "removed", reason=reason, created=CREATED, superseded_by="S-0002"
    )


BARE = WorkItemDetail("S-0001", "a title", "removed", "", [])


def test_status_lists_a_removed_work_item_as_superseded_by_the_other() -> None:
    assert status_text([removed("")]) == (
        "backlog (0)\nin-progress (0)\ncompleted (0)\nremoved (1)\n"
        "  S-0001  a title\n"
        "  superseded by S-0002\n"
    )


def test_status_lists_what_supersedes_it_before_a_reason_given_beside_it() -> None:
    assert status_text([removed("refiled")]).endswith(
        "  S-0001  a title\n  superseded by S-0002, refiled\n"
    )


def test_show_lists_what_supersedes_a_removed_work_item() -> None:
    assert "  superseded by S-0002\n" in show_text(replace(BARE, superseded_by="S-0002"))


def test_show_lists_what_a_work_item_supersedes() -> None:
    assert "  supersedes   S-0003, S-0004\n" in show_text(
        replace(BARE, supersedes=["S-0003", "S-0004"])
    )


def test_show_lists_none_of_it_for_a_work_item_that_has_none() -> None:
    assert "supersede" not in show_text(BARE)
