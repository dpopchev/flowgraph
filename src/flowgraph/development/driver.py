"""What the driver of the development asks of a start: `[development] driver` of the configuration.

With the development on and the driver an agent, a work item in Backlog is started only once it
holds a complexity beside its Task, so the coordinator can evaluate it and pick the model. A
developer drives it by default and asks nothing, and the development off asks nothing whoever
drives it. Which model a complexity maps to stays outside fgraph.
"""

from typing import assert_never

from flowgraph.item.commands import ItemIdError, parse_item_id
from flowgraph.record import Config
from flowgraph.record.layers import Driver
from flowgraph.task import TaskId
from flowgraph.work_item import (
    LoadWorkItem,
    WorkItem,
    WorkItemId,
    work_item_id_text,
)

# The refusal of a work item with no complexity, with the id of it in both places.
NO_COMPLEXITY = (
    "{id} has no complexity to start with: "
    "set it with fgraph amend {id} --complexity low, medium or high"
)


class NoComplexityError(ValueError):
    """A work item started while the driver asks a complexity and it holds none; names it."""


def asks_complexity(config: Config) -> bool:
    """True when the development is on and driven by an agent, which asks a complexity to start."""
    return config.development.enabled and config.development.driver is Driver.AGENT


def check_complexity(item: str, load_work_item: LoadWorkItem, config: Config) -> None:
    """Check that the start of the item of that id holds the complexity the driver asks.

    Raises NoComplexityError for a work item in Backlog that holds a Task and no complexity. One
    with no Task and one past Backlog are left to the start, which refuses them in its own words,
    and so are a Task, a Feature and a text that is no id. Nothing is read unless the driver asks.
    """
    if not asks_complexity(config):
        return
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    match item_id:
        case TaskId():
            return
        case WorkItemId():
            held = load_work_item(item_id)
        case _ as unreachable:
            assert_never(unreachable)
    match held:
        case WorkItem(tasks=()):
            return
        case WorkItem(complexity=None):
            raise NoComplexityError(NO_COMPLEXITY.format(id=work_item_id_text(item_id)))
        case _:
            return
