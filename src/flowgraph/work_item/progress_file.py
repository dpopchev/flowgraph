"""The progress lines of a work item as its file holds them: one table each, in the order noted.

A table holds the text and the time noted, and the id of its Task as written when it names one.
"""

from pydantic import BaseModel, ConfigDict

from flowgraph.item import HeldTime
from flowgraph.task import parse_task_id, task_id_text
from flowgraph.work_item.progress import ProgressLine, make_progress_line


class ProgressFile(BaseModel):
    """One table of the progress of a work item file: its text, its time and its Task, if any."""

    model_config = ConfigDict(extra="forbid")

    text: str
    noted: HeldTime
    task: str = ""


class ProgressTables(BaseModel):
    """What the file of a work item holds of its progress lines; none when it has none."""

    progress: list[ProgressFile] = []


def progress_primitives(line: ProgressLine) -> dict[str, object]:
    """The line as the primitives its table holds: its Task only when it names one."""
    task = {} if line.task is None else {"task": task_id_text(line.task)}
    return {"text": line.text, "noted": line.noted, **task}


def progress_held(held: ProgressFile) -> ProgressLine:
    """The line a validated table holds, built through its constructor.

    Raises EmptyPartError when its text is blank and TaskIdError when its Task is no Task id.
    """
    task = parse_task_id(held.task) if held.task else None
    return make_progress_line(held.text, held.noted, task)
