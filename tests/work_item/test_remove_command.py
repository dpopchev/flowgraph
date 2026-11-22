"""The remove command of a work item, and the text that lists a removed work item."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.status import show_text, status_text
from flowgraph.work_item import (
    RemovedAlreadyError,
    WorkItemDetail,
    WorkItemRow,
    WorkItemState,
    make_kind,
    make_work_item,
    make_work_item_id,
    remove_work_item,
    removed_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
CREATED = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 1, 3, tzinfo=UTC)
ITEM = make_work_item(ONE, "a title", make_scenario("a", "b", "c"), "", CREATED)
GONE = removed_work_item(ITEM, "filed by mistake", NOW)


@pytest.mark.command
def test_a_work_item_is_removed_and_saved_whole() -> None:
    saved: list[WorkItemState] = []
    remove_work_item(
        item_id=ONE,
        reason="filed by mistake",
        load_work_item=lambda _: ITEM,
        save_work_item=saved.append,
        now=lambda: NOW,
    )
    assert saved == [GONE]


@pytest.mark.command
def test_a_remove_refused_saves_nothing() -> None:
    saved: list[WorkItemState] = []
    with pytest.raises(RemovedAlreadyError):
        remove_work_item(
            item_id=ONE,
            reason="a reason",
            load_work_item=lambda _: GONE,
            save_work_item=saved.append,
            now=lambda: NOW,
        )
    assert saved == []


@pytest.mark.view
def test_a_removed_work_item_is_listed_under_removed_with_its_reason() -> None:
    rows = [
        WorkItemRow("CH-0002", "another title", "backlog", created=CREATED),
        WorkItemRow("CH-0001", "a title", "removed", reason="filed by mistake", created=CREATED),
    ]
    assert status_text(rows) == (
        "Backlog (1)\n"
        "  CH-0002  another title\n"
        "InProgress (0)\n"
        "Completed (0)\n"
        "Removed (1)\n"
        "  CH-0001  a title  -- filed by mistake\n"
    )


@pytest.mark.view
def test_a_record_with_nothing_removed_lists_no_removed_heading() -> None:
    rows = [WorkItemRow("CH-0002", "another title", "backlog", created=CREATED)]
    assert status_text(rows).splitlines()[-1] == "Completed (0)"


@pytest.mark.view
def test_a_removed_work_item_is_shown_with_its_bucket_and_its_reason() -> None:
    detail = WorkItemDetail(
        id="CH-0001",
        title="a title",
        state="removed",
        description="",
        given="a",
        when="b",
        then="c",
        tasks=[],
        reason="filed by mistake",
    )
    assert show_text(detail).splitlines()[:3] == [
        "CH-0001  a title",
        "  bucket       Removed",
        "  reason       filed by mistake",
    ]
