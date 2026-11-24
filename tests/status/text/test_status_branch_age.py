"""The text of status under a started work item whose branch is older than its age.

The age is the word of `development.branch_max`, `1d`, set on the row by the store that reads the
clock; it says so on a line below the title, before a block, and says nothing for a row without it.
"""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import status_text
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
TASKS = [
    TaskRow("T-0001", "a task title", "an output", "", "completed", "abc1234"),
    TaskRow("T-0002", "a task title", "an output", "", "backlog"),
]
OLD = "  its branch is older than 1d"


def row(state: str = "started", older: str = "1d", agent: str = "") -> WorkItemRow:
    """The Story S-0001 in that state, with its Tasks, its agent and the age its branch passes."""
    return WorkItemRow(
        "S-0001",
        "a title",
        state,
        commit="abc1234" if state == "completed" else "",
        created=CREATED,
        tasks=TASKS,
        agent=agent,
        branch_older_than=older,
    )


def test_a_started_work_item_with_an_older_branch_says_the_age_on_a_line_below_its_own() -> None:
    assert status_text([row()]).splitlines()[2:4] == ["  S-0001  1/2 T  a title", OLD]


def test_a_started_work_item_without_an_older_branch_is_listed_as_before() -> None:
    assert status_text([row(older="")]).splitlines()[2] == "  S-0001  1/2 T  a title"


def test_an_older_branch_keeps_the_agent_before_the_title_and_the_word_below_it() -> None:
    lines = status_text([row(agent="sonnet-a1")]).splitlines()[2:4]
    assert lines == ["  S-0001  1/2 T  [sonnet-a1]  a title", OLD]


def test_an_older_branch_of_a_blocked_work_item_precedes_its_block() -> None:
    blocked = WorkItemRow(
        "S-0001",
        "a title",
        "blocked",
        created=CREATED,
        tasks=TASKS,
        block_reason="no key",
        waiting_on="developer",
        branch_older_than="1d",
    )
    assert status_text([blocked]).splitlines()[2:5] == [
        "! S-0001  1/2 T  a title",
        OLD,
        "  waiting on developer: no key",
    ]


def test_an_older_branch_under_a_feature_is_two_columns_further_in() -> None:
    feature = FeatureRow("F-0001", "a feature", "InProgress", 0, 1, started=[row()])
    assert status_text([feature]).splitlines()[3:5] == [
        "    S-0001  1/2 T  a title",
        f"  {OLD}",
    ]


def test_a_work_item_in_backlog_holding_an_older_age_is_listed_as_before() -> None:
    assert status_text([row(state="backlog")]).splitlines()[1] == "  S-0001  [2 T]  a title"


def test_a_completed_work_item_holding_an_older_age_is_listed_as_before() -> None:
    assert status_text([row(state="completed")]).splitlines()[3] == "  S-0001  abc1234  a title"
