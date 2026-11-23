"""The agent a started work item is handed to: one opaque word, named by the start.

The word is at most 32 letters, digits and `. _ : / -`; what it names is up to whoever reads it.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from flowgraph.record import DEVELOPMENT_ENABLED

# One word of at most 32 ASCII letters, digits and the marks `. _ : / -`.
AGENT = re.compile(r"[A-Za-z0-9._:/-]{1,32}")


@dataclass(frozen=True)
class Agent:
    """The name of the agent a work item is handed to."""

    name: str


class AgentError(ValueError):
    """A text that is no agent, or an agent named where a start takes none."""


def make_agent(text: str) -> Agent:
    """The agent the text names; raises AgentError when it is not one word of the marks above."""
    if AGENT.fullmatch(text) is None:
        raise AgentError(
            f"{text!r} is no agent: it is one word of at most 32 letters, digits and . _ : / -"
        )
    return Agent(text)


def agent_written(text: str) -> Agent | None:
    """The agent a file holds as text; none for the empty text a work item without one holds."""
    return make_agent(text) if text else None


def check_agent_taken(
    item: str, agent: str | None, development_on: bool, config_file: Path
) -> None:
    """Refuse an agent given to the start of the item when it is no agent or none is handed work.

    Raises AgentError when the text is no agent, and naming the key that turns the development
    on, in that file, when an agent is given while the development is off.
    """
    if agent is None:
        return
    make_agent(agent)
    if not development_on:
        turn_on = f"set {DEVELOPMENT_ENABLED} = true in {config_file}"
        raise AgentError(
            f"{item} takes no --agent: the development is off, so no agent is handed work"
            f" -- {turn_on}"
        )
