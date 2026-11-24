"""The text of fgraph show for a removed Task: in Removed, with the reason it was removed."""

import pytest

from flowgraph.status import show_text
from flowgraph.task import TaskRow
from flowgraph.work_item import WorkItemDetail

pytestmark = pytest.mark.view


def shown(task: TaskRow) -> list[str]:
    """The lines show lists for the Task of a started work item, from its title on."""
    detail = WorkItemDetail(
        "S-0001",
        "a title",
        "started",
        "",
        [task],
        given="a state",
        when="an action",
        then="another",
    )
    return show_text(detail).splitlines()[6:]


def test_a_removed_task_is_shown_in_removed_with_its_reason() -> None:
    gone = TaskRow("T-0001", "a task", "an output", "", "removed", reason="not needed")
    assert shown(gone) == [
        "  T-0001  a task",
        "    bucket           Removed",
        "    reason           not needed",
        "    expected output  an output",
    ]


def test_a_task_in_backlog_is_shown_with_no_bucket_and_no_reason() -> None:
    waiting = TaskRow("T-0001", "a task", "an output", "", "backlog")
    assert shown(waiting) == ["  T-0001  a task", "    expected output  an output"]
