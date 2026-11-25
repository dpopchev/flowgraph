"""The closing of fgraph mcp: the tools a coordinator lands a work item and answers its closing by.

Each is the command of the same name run on main. No tool takes the approval of a landing: under
development.approver = developer the landing is refused saying it waits for the developer (HELD of
src/flowgraph/development/approval.py), who approves it with fgraph land ID --approved on the
command line (the decision of F-0022).
"""

from typing import Literal

from pydantic import Field

from flowgraph.mcp.moves import ItemArguments
from flowgraph.mcp.tools import Tool


class LandArguments(ItemArguments):
    """The arguments of land: the message of the commit the landing makes."""

    message: str | None = Field(
        default=None,
        description="the message of the commit the landing makes: needed by merge-commit, squash",
    )


class VerifyArguments(ItemArguments):
    """The arguments of verify: the answer of the closing and the text that backs it."""

    answer: Literal["yes", "no"] = Field(description="yes when the criterion holds, else no")
    text: str = Field(description="what the run of its criterion printed")


def _land(given: LandArguments) -> list[str]:
    return [
        "land",
        given.id,
        *([f"--message={given.message}"] if given.message is not None else []),
    ]


def _verify(given: VerifyArguments) -> list[str]:
    return ["verify", given.id, f"--{given.answer}={given.text}"]


CLOSING_TOOLS = (
    Tool(
        "land",
        "Land a work item on main; it answers with the line fgraph land prints",
        LandArguments,
        _land,
    ),
    Tool(
        "verify",
        "Keep the answer of the closing of a completed work item; it answers with the line "
        "fgraph verify prints; a no files a Bug that amends it",
        VerifyArguments,
        _verify,
    ),
)
