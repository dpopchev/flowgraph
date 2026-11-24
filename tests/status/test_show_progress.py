"""The text of fgraph show for progress lines: those of a Task under it, the rest under Progress."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from flowgraph.knowledge import KnowledgeRow
from flowgraph.status import show_text
from flowgraph.task import TaskRow
from flowgraph.work_item import ProgressRow, WorkItemDetail

pytestmark = pytest.mark.view

ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 3, 9, 0, 0, tzinfo=UTC)
TASKS = [
    TaskRow("T-0001", "a task title", "an output", "how", "started"),
    TaskRow("T-0002", "another title", "an output", "", "backlog"),
]


def noted() -> list[ProgressRow]:
    """A line of the work item, then two of T-0001."""
    return [
        ProgressRow(ON, "the parser is read", ""),
        ProgressRow(ON, "red: 1 failed", "T-0001"),
        ProgressRow(LATER, "green", "T-0001"),
    ]


def detail(
    progress: list[ProgressRow] | None = None, knowledge: list[KnowledgeRow] | None = None
) -> WorkItemDetail:
    """A started Story with two Tasks, the knowledge given and the progress given, if any.

    With no progress given the detail is built without the argument.
    """
    built = WorkItemDetail(
        "S-0001",
        "a title",
        "started",
        "",
        list(TASKS),
        given="a state",
        when="an action",
        then="another",
        knowledge=knowledge or [],
    )
    return built if progress is None else replace(built, progress=progress)


def lines_between(text: str, first: str, last: str) -> list[str]:
    """The lines of the text from the line first up to, not with, the line last."""
    lines = text.splitlines()
    return lines[lines.index(first) : lines.index(last)]


def test_the_lines_of_a_task_follow_its_description_in_the_order_noted() -> None:
    text = show_text(detail(progress=noted()))
    assert lines_between(text, "  T-0001  a task title", "  T-0002  another title") == [
        "  T-0001  a task title",
        "    bucket           InProgress",
        "    expected output  an output",
        "    description      how",
        "    progress         2026-01-02  red: 1 failed",
        "    progress         2026-01-03  green",
    ]


def test_a_task_with_no_line_is_shown_with_none() -> None:
    text = show_text(detail(progress=noted()))
    after = lines_between(text, "  T-0002  another title", "Progress (1)")
    assert [line for line in after if "progress" in line] == []


def test_the_lines_of_the_work_item_follow_under_progress() -> None:
    text = show_text(detail(progress=noted()))
    assert text.endswith("Progress (1)\n  2026-01-02  the parser is read\n")


def test_no_progress_heading_is_shown_when_every_line_names_a_task() -> None:
    of_tasks = [line for line in noted() if line.task]
    text = show_text(detail(progress=of_tasks))
    assert [line for line in text.splitlines() if line.startswith("Progress (")] == []


def test_the_lines_of_the_work_item_follow_the_knowledge_lines() -> None:
    knowledge = [KnowledgeRow("finding", ON, "a fact")]
    text = show_text(detail(progress=noted(), knowledge=knowledge))
    assert text.endswith(
        "Knowledge (1)\n  finding  2026-01-02  a fact\n"
        "Progress (1)\n  2026-01-02  the parser is read\n"
    )


def test_a_work_item_with_no_progress_line_is_shown_as_before() -> None:
    assert show_text(detail(progress=[])) == show_text(detail())
