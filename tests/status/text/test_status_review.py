"""The text of status for a started work item ready for review, marked `@` in the first column."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureRow
from flowgraph.status import cut_lines, same_top, status_text
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
DONE = TaskRow("T-0001", "a done task", "an output", "", "completed", "abc1234")
LATER = TaskRow("T-0002", "a later task", "an output", "", "backlog")


def started(number: int, *tasks: TaskRow, agent: str = "") -> WorkItemRow:
    """A started Story of that number holding the Tasks, handed to the agent if any."""
    return WorkItemRow(
        f"S-{number:04}",
        f"title {number}",
        "started",
        created=CREATED,
        agent=agent,
        tasks=list(tasks),
    )


def progress(text: str) -> list[str]:
    """The lines of the text between the heading of InProgress and that of Completed."""
    lines = text.splitlines()
    first = next(at for at, line in enumerate(lines) if line.startswith("in-progress"))
    return lines[first + 1 : lines.index("completed (0)")]


def test_a_started_work_item_with_every_task_completed_is_marked_with_an_at_sign() -> None:
    assert progress(status_text([started(1, DONE)])) == ["@ S-0001  1/1 T  title 1"]


def test_the_marked_line_keeps_the_agent_before_the_title() -> None:
    assert progress(status_text([started(1, DONE, agent="sonnet-1")])) == [
        "@ S-0001  1/1 T  [sonnet-1]  title 1"
    ]


def test_a_started_work_item_with_a_task_in_backlog_is_not_marked() -> None:
    assert progress(status_text([started(1, DONE, LATER)])) == ["  S-0001  1/2 T  title 1"]


def test_a_marked_work_item_is_marked_under_its_feature_two_columns_further_in() -> None:
    feature = FeatureRow(
        "F-0001",
        "a feature",
        "in-progress",
        0,
        1,
        started=[started(1, DONE)],
        is_started=True,
    )
    assert progress(status_text([feature]))[1:] == ["  @ S-0001  1/1 T  title 1"]


def test_a_marked_line_cut_to_a_width_keeps_the_mark() -> None:
    cut = cut_lines(status_text([started(1, DONE)]), 12)
    assert cut.splitlines()[2] == "@ S-0001 ..."


def test_a_marked_work_item_beyond_the_top_is_listed_after_the_top() -> None:
    rows = [started(number, LATER) for number in range(1, 7)] + [started(7, DONE)]
    assert progress(status_text(rows, same_top(5)))[5:] == [
        "@ S-0007  1/1 T  title 7",
        "  ... 1 more",
    ]
