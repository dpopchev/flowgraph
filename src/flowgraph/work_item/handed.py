"""The hand of a started work item to an agent, and the agent a work item holds as text."""

from dataclasses import replace
from typing import assert_never

from flowgraph.work_item.agent import Agent
from flowgraph.work_item.model import (
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemState,
)


def handed_work_item(started: StartedWorkItem, agent: Agent | None) -> StartedWorkItem:
    """The started work item handed to the agent; as it was when there is none."""
    return replace(started, agent=agent)


def agent_text(item: WorkItemState) -> str:
    """The name of the agent a started or completed work item holds; empty for none or any other."""
    match item:
        case StartedWorkItem(agent=Agent() as agent) | CompletedWorkItem(agent=Agent() as agent):
            return agent.name
        case StartedWorkItem() | CompletedWorkItem() | WorkItem() | RemovedWorkItem():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
