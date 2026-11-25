"""The moves of fgraph mcp: the tools an agent moves its work item and its Tasks by.

Each is the command of the same name run in the directory the call names, on main or in the
worktree of the work item, and is written where fgraph writes it (S-0159, docs/domain-model.md,
Persistence, Who writes what). A text is given as --option=value, since argparse reads a text that
starts with a dash as an option otherwise (probed on 2026-11-25: fgraph note S-0001 --finding --x
exits 2, --finding=--x is noted).
"""

from typing import Literal

from pydantic import Field

from flowgraph.mcp.tools import Tool, ToolArguments

ID = "the id of the work item or of its Task, as S-0001 or T-0001"
AGENT = "the agent a work item is handed to, one word of at most 32 letters, digits and . _ : / -"


class ItemArguments(ToolArguments):
    """The arguments of a move: the directory and the id of the item it moves."""

    id: str = Field(description=ID)


class StartArguments(ToolArguments):
    """The arguments of start: the item to start, or none for the first that can start."""

    id: str | None = Field(
        default=None,
        description=(
            "the id of the work item or of its Task, as S-0001 or T-0001; left out, the first"
            " line of the Backlog that can start"
        ),
    )
    agent: str | None = Field(default=None, description=AGENT)


class HandArguments(ItemArguments):
    """The arguments of hand: the agent the work item is handed to."""

    agent: str = Field(description=AGENT)


class BlockArguments(ItemArguments):
    """The arguments of block: why the item waits and on whom."""

    reason: str = Field(description="why the item cannot go on")
    waiting_on: str = Field(description="who or what the item waits on")


class NoteArguments(ItemArguments):
    """The arguments of note: the kind of the note and its text."""

    kind: Literal["finding", "decision", "deviation", "progress"] = Field(
        description="the kind of the note"
    )
    text: str = Field(description="the text of the note")


class CompleteArguments(ItemArguments):
    """The arguments of complete: the commit that holds the work."""

    commit: str | None = Field(
        default=None, description="the commit that holds its work: needed with the development on"
    )


def _start(given: StartArguments) -> list[str]:
    return [
        "start",
        *([given.id] if given.id is not None else []),
        *([f"--agent={given.agent}"] if given.agent is not None else []),
    ]


def _hand(given: HandArguments) -> list[str]:
    return ["hand", given.id, f"--agent={given.agent}"]


def _block(given: BlockArguments) -> list[str]:
    return ["block", given.id, f"--reason={given.reason}", f"--waiting-on={given.waiting_on}"]


def _unblock(given: ItemArguments) -> list[str]:
    return ["unblock", given.id]


def _note(given: NoteArguments) -> list[str]:
    return ["note", given.id, f"--{given.kind}={given.text}"]


def _complete(given: CompleteArguments) -> list[str]:
    return [
        "complete",
        given.id,
        *([f"--commit={given.commit}"] if given.commit is not None else []),
    ]


ANSWERS = "; it answers with the line the command prints"

MOVE_TOOLS = (
    Tool(
        "start",
        "Start a work item, or a Task of it; with no id, the first work item of the Backlog that"
        " can start, which an agent claims; handed to the agent when one is named" + ANSWERS,
        StartArguments,
        _start,
    ),
    Tool("hand", "Hand a started work item to an agent" + ANSWERS, HandArguments, _hand),
    Tool(
        "block",
        "Block a work item or a Task, with the reason and what it waits on" + ANSWERS,
        BlockArguments,
        _block,
    ),
    Tool("unblock", "Unblock a blocked work item or Task" + ANSWERS, ItemArguments, _unblock),
    Tool(
        "note",
        "Note a finding, a decision, a deviation or the progress of an item" + ANSWERS,
        NoteArguments,
        _note,
    ),
    Tool(
        "complete",
        "Complete a Task at the commit of its work, refused when its check fails" + ANSWERS,
        CompleteArguments,
        _complete,
    ),
)
