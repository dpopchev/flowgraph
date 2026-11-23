"""The text of status under a started work item handed to an agent: the agent between the
progress and the title, so a line cut to the width keeps it."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import cut_lines, status_text
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
TASKS = [
    TaskRow("T-0001", "a task title", "an output", "", "completed", "abc1234"),
    TaskRow("T-0002", "a task title", "an output", "", "backlog"),
]


def handed(agent: str = "sonnet-a1") -> WorkItemRow:
    """A started work item with two Tasks, one completed, handed to the agent given."""
    return WorkItemRow("S-0001", "a title", "started", created=CREATED, tasks=TASKS, agent=agent)


def test_a_started_work_item_lists_its_agent_between_the_progress_and_the_title() -> None:
    assert status_text([handed()]).splitlines()[2] == "  S-0001  1/2 T  [sonnet-a1]  a title"


def test_a_started_work_item_under_a_feature_lists_its_agent_two_columns_further_in() -> None:
    feature = FeatureRow("F-0001", "a feature", "InProgress", 0, 1, started=[handed()])
    assert status_text([feature]).splitlines()[2:4] == [
        "  F-0001  0/1 W  a feature",
        "    S-0001  1/2 T  [sonnet-a1]  a title",
    ]


def test_a_line_cut_to_the_width_keeps_the_agent() -> None:
    cut = cut_lines(status_text([handed()]), 35)
    assert cut.splitlines()[2] == "  S-0001  1/2 T  [sonnet-a1]  a ..."


def test_a_started_work_item_without_an_agent_is_listed_as_before() -> None:
    rows = [WorkItemRow("S-0001", "a title", "started", created=CREATED, tasks=TASKS)]
    assert status_text(rows).splitlines()[2] == "  S-0001  1/2 T  a title"
