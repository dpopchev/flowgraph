"""A progress line: where the work of a work item stands, kept on it in the order it was noted.

A progress line is a hand-off, a red line, a structure note. It is no knowledge line, so fgraph
knowledge never lists it: it is about no term and governs no file. It is never amended or
removed.
"""

from dataclasses import dataclass
from datetime import datetime

from flowgraph.criterion import said
from flowgraph.task import TaskId, task_id_text


@dataclass(frozen=True)
class ProgressLine:
    """One progress line: its text, when it was noted and the Task it is of, if any.

    The Task is one of the work item that keeps the line; none for a line of the work item itself.
    """

    text: str
    noted: datetime
    task: TaskId | None = None


@dataclass
class ProgressRow:
    """One progress line as plain data, as a view reads it: the id of its Task, "" for none."""

    noted: datetime
    text: str
    task: str = ""


def make_progress_line(text: str, noted: datetime, task: TaskId | None = None) -> ProgressLine:
    """The line of that text, noted at that time, kept to the second, of the Task given if any.

    Raises EmptyPartError naming the text when it is blank.
    """
    return ProgressLine(said("text", text), noted.replace(microsecond=0), task)


def progress_row(line: ProgressLine) -> ProgressRow:
    """The line as the row a view reads."""
    return ProgressRow(line.noted, line.text, "" if line.task is None else task_id_text(line.task))
