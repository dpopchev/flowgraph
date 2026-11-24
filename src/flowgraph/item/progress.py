"""The progress line of a work item or of a Task of it, named by its id: what the write says."""

from collections.abc import Sequence
from typing import assert_never

from flowgraph.item.commands import MESSAGE, Written
from flowgraph.item.id import parse_moved_id
from flowgraph.item.moves import load_holder
from flowgraph.parent import FeatureId, feature_id_text
from flowgraph.record import Now
from flowgraph.record.store import Store
from flowgraph.task import TaskId, task_id_text
from flowgraph.work_item import (
    WorkItemId,
    make_progress_line,
    progressed_work_item,
    work_item_id_text,
)


class ProgressLineError(ValueError):
    """A progress line asked for what it does not take: a Feature, a term or a file."""


def note_progress(
    item: str,
    text: str,
    store: Store,
    now: Now,
    about: Sequence[str] | None = None,
    governs: Sequence[str] | None = None,
) -> Written:
    """Keep the progress line on the work item of that id, or on the one that holds the Task.

    The line of a Task names it. Raises ProgressLineError for a Feature or with terms or files,
    ItemIdError when the text is no id, WorkItemNotFoundError or TaskNotFoundError when the
    record holds no such item and EmptyPartError when the text is blank; nothing is saved.
    """
    if about or governs:
        raise ProgressLineError(
            "a progress line takes no --about and no --governs: it is no knowledge line"
        )
    match parse_moved_id(item):
        case FeatureId() as it:
            raise ProgressLineError(
                f"{feature_id_text(it)} keeps no progress line: "
                "fgraph note --progress takes a work item or a Task of it"
            )
        case WorkItemId() as item_id:
            held = store.load_work_item(item_id)
            store.save_work_item(progressed_work_item(held, make_progress_line(text, now())))
            named = work_item_id_text(item_id)
        case TaskId() as task_id:
            holder = load_holder(store)(task_id)
            line = make_progress_line(text, now(), task_id)
            store.save_work_item(progressed_work_item(holder, line))
            named = f"{task_id_text(task_id)} of {work_item_id_text(holder.id)}"
        case _ as unreachable:
            assert_never(unreachable)
    return Written(f"noted {named}\n", MESSAGE.format(f"note {named}"))
