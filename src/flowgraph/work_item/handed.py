"""The hand of a started work item to an agent, and the agent a work item holds as text."""

from dataclasses import replace
from typing import assert_never

from flowgraph.task import CompletedAlreadyError, NotStartedError
from flowgraph.work_item.agent import Agent
from flowgraph.work_item.id import WorkItemId, work_item_id_text
from flowgraph.work_item.model import (
    CompletedWorkItem,
    LoadWorkItem,
    RemovedAlreadyError,
    RemovedWorkItem,
    SaveWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
)


def handed_work_item(started: StartedWorkItem, agent: Agent | None) -> StartedWorkItem:
    """The started work item handed to the agent; as it was when there is none."""
    return replace(started, agent=agent)


def handed_over(item: WorkItemState, agent: Agent) -> StartedWorkItem:
    """The started work item handed to the agent in place of the one it held.

    Raises NotStartedError when it is in Backlog, CompletedAlreadyError when it is completed and
    RemovedAlreadyError when it is removed.
    """
    match item:
        case StartedWorkItem():
            return handed_work_item(item, agent)
        case WorkItem():
            named = work_item_id_text(item.id)
            raise NotStartedError(f"{named} is in Backlog: its start names the agent with --agent")
        case CompletedWorkItem():
            raise CompletedAlreadyError(f"{work_item_id_text(item.id)} is completed already")
        case RemovedWorkItem():
            raise RemovedAlreadyError(item.id)
        case _ as unreachable:
            assert_never(unreachable)


def hand_work_item(
    *, item_id: WorkItemId, agent: Agent, load_work_item: LoadWorkItem, save_work_item: SaveWorkItem
) -> None:
    """Hand the started work item of that id to the agent and save it whole.

    Raises WorkItemNotFoundError when the record holds no such item, or the refusal of
    handed_over; nothing is saved.
    """
    save_work_item(handed_over(load_work_item(item_id), agent))


def agent_text(item: WorkItemState) -> str:
    """The name of the agent a started or completed work item holds; empty for none or any other."""
    match item:
        case StartedWorkItem(agent=Agent() as agent) | CompletedWorkItem(agent=Agent() as agent):
            return agent.name
        case StartedWorkItem() | CompletedWorkItem() | WorkItem() | RemovedWorkItem():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
