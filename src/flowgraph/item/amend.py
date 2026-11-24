"""The amend of a Task named by its id: the parts an amend states, read as those of a Task."""

from collections.abc import Sequence
from dataclasses import fields

from flowgraph import work_item
from flowgraph.item.commands import MESSAGE, Written
from flowgraph.item.moves import load_holder
from flowgraph.record.store import Store
from flowgraph.task import TaskAmendment, parse_task_id, task_id_text
from flowgraph.work_item import Amendment, NoSuchPartError, work_item_id_text

ONLY_A_TASK = "a Task is amended by its title, its output, its check and its description"

# The parts of an amend that are a Task's.
TASK_PARTS = ("title", "description", "output", "check")


def _of_task(named: str, parts: Amendment, criteria: Sequence[str] | None) -> TaskAmendment:
    """The amendment of the Task of that name the parts of an amend and its criteria state.

    Raises NoSuchPartError naming the criteria and each part given that is no part of a Task.
    """
    foreign = ["criteria"] if criteria is not None else []
    foreign += [
        part.name
        for part in fields(parts)
        if part.name not in TASK_PARTS and getattr(parts, part.name) is not None
    ]
    if foreign:
        raise NoSuchPartError(f"{named} has no {', '.join(foreign)}: {ONLY_A_TASK}")
    return TaskAmendment(parts.title, parts.output, parts.check, parts.description)


def amend_task_item(
    item: str, parts: Amendment, criteria: Sequence[str] | None, store: Store
) -> Written:
    """Amend the Task in Backlog of that id in the work item that holds it; what the write says.

    Raises TaskIdError when the text is no Task id, NoSuchPartError when a part is given that no
    Task has, TaskNotFoundError when the record holds no such Task, or the refusal of the amend of
    a Task; nothing is saved.
    """
    task_id = parse_task_id(item)
    task = task_id_text(task_id)
    amendment = _of_task(task, parts, criteria)
    holder = work_item.amend_task(
        task_id=task_id,
        amendment=amendment,
        load_holder=load_holder(store),
        save_work_item=store.save_work_item,
    )
    named = f"{task} of {work_item_id_text(holder)}"
    return Written(f"amended {named}\n", MESSAGE.format(f"amend {named}"))
