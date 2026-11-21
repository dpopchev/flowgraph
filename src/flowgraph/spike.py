"""A Spike: a question to answer, the kind of work item whose ids are written `Q-0001`.

Q stands for question. Its criterion is a hypothesis; it is completed with the decision that
answers it. Each Spike name stands for the name of the shared work item (`flowgraph.work_item`).
"""

from collections.abc import Collection

from flowgraph.criterion import Hypothesis
from flowgraph.work_item import (
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemId,
    WorkItemIdError,
    WorkItemState,
    make_kind,
    make_work_item,
    make_work_item_id,
    next_work_item_id,
    parse_work_item_id,
    work_item_id_text,
)

# The kind of a Spike.
SPIKE = make_kind("Spike", "a", "Q", Hypothesis)

SpikeId = WorkItemId
Spike = WorkItem
StartedSpike = StartedWorkItem
CompletedSpike = CompletedWorkItem
RemovedSpike = RemovedWorkItem
SpikeState = WorkItemState
SpikeIdError = WorkItemIdError

make_spike = make_work_item
spike_id_text = work_item_id_text


def make_spike_id(number: int) -> SpikeId:
    """The id of the Spike with that number; raises SpikeIdError when it is below 1."""
    return make_work_item_id(SPIKE, number)


def parse_spike_id(text: str) -> SpikeId:
    """The Spike id written as the text; raises SpikeIdError when it is not `Q-` and a number."""
    return parse_work_item_id(SPIKE, text)


def next_spike_id(taken: Collection[SpikeId]) -> SpikeId:
    """The next free Spike id: one above the highest taken, the first when none is."""
    return next_work_item_id(SPIKE, taken)
