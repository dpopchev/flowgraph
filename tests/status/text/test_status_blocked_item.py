"""The text of status under InProgress for a blocked work item: marked `!` with its block."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import status_text
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
DONE = TaskRow("T-0001", "a done task", "an output", "", "completed", "abc1234")
BEGUN = TaskRow("T-0002", "a begun task", "an output", "", "started")
HELD = TaskRow("T-0003", "a held task", "an output", "", "blocked", "", "no review", "a reviewer")
MARKED = "! S-0001  0/1 T  title 1  -- waiting on developer: no key"


def blocked(*tasks: TaskRow, agent: str = "", parent: str = "") -> WorkItemRow:
    """The blocked Story S-0001 holding the Tasks, waiting on the developer for a key."""
    return WorkItemRow(
        "S-0001",
        "title 1",
        "blocked",
        parent=parent,
        created=CREATED,
        started=CREATED,
        agent=agent,
        block_reason="no key",
        waiting_on="developer",
        tasks=list(tasks),
    )


def test_a_blocked_work_item_is_listed_under_inprogress_marked_with_what_it_waits_on() -> None:
    assert status_text([blocked(BEGUN)]).splitlines()[1:3] == ["InProgress (1)", MARKED]


def test_a_blocked_work_item_with_an_agent_names_it_in_brackets_before_its_title() -> None:
    assert status_text([blocked(BEGUN, agent="opus-b2")]).splitlines()[2] == (
        "! S-0001  0/1 T  [opus-b2]  title 1  -- waiting on developer: no key"
    )


def test_the_started_task_of_a_blocked_work_item_is_listed_under_it() -> None:
    assert status_text([blocked(BEGUN)]).splitlines()[2:4] == [
        MARKED,
        "    => T-0002  a begun task",
    ]


def test_a_blocked_work_item_with_every_task_completed_is_marked_blocked_and_not_for_review() -> (
    None
):
    assert status_text([blocked(DONE)]).splitlines()[2] == (
        "! S-0001  1/1 T  title 1  -- waiting on developer: no key"
    )


def test_a_blocked_work_item_under_a_feature_is_listed_two_columns_further_in() -> None:
    under = blocked(BEGUN, parent="F-0001")
    feature = FeatureRow("F-0001", "a feature title", "InProgress", 0, 1, started=[under])
    assert status_text([feature]).splitlines()[3] == f"  {MARKED}"


def test_a_feature_is_marked_by_its_blocked_work_item() -> None:
    under = blocked(BEGUN, parent="F-0001")
    feature = FeatureRow("F-0001", "a feature title", "InProgress", 0, 1, started=[under])
    assert status_text([feature]).splitlines()[2] == (
        "! F-0001  0/1 W  a feature title  -- waiting on developer: no key"
    )


def test_the_block_of_a_feature_comes_before_that_of_its_blocked_work_item() -> None:
    under = blocked(BEGUN, parent="F-0001")
    feature = FeatureRow(
        "F-0001",
        "a feature title",
        "InProgress",
        0,
        1,
        started=[under],
        waiting_on="a sponsor",
        block_reason="no budget",
    )
    assert status_text([feature]).splitlines()[2:4] == [
        "! F-0001  0/1 W  a feature title  -- waiting on a sponsor: no budget",
        f"  {MARKED}",
    ]


def test_the_block_of_a_work_item_comes_before_that_of_a_task_of_it() -> None:
    under = blocked(HELD, parent="F-0001")
    feature = FeatureRow("F-0001", "a feature title", "InProgress", 0, 1, started=[under])
    assert status_text([feature]).splitlines()[2] == (
        "! F-0001  0/1 W  a feature title  -- waiting on developer: no key"
    )
