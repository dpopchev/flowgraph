"""A tool of fgraph mcp is one command of fgraph an agent calls over stdio.

It names its arguments as a pydantic model, which is both the JSON Schema tools/list gives and the
check of the arguments of a call; the command it runs is the argv of fgraph it builds from them,
run in the directory the call names; what the command printed is the result, its output when it
exits 0, else its one line of refusal as a tool error.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

DIRECTORY = (
    "the directory fgraph runs in, as a shell would run it there: "
    "the checkout of main or the worktree of a work item"
)

# The refusal of the arguments of a call: the tool, the first field refused and pydantic's message.
REFUSED_ARGUMENTS = "the arguments of {tool} are refused: {field}: {message}"


class ToolArgumentsError(ValueError):
    """The arguments of a call are not those of its tool."""


class ToolArguments(BaseModel):
    """The arguments every tool takes, the base of each tool's own."""

    model_config = ConfigDict(extra="forbid")

    directory: str = Field(description=DIRECTORY)


@dataclass(frozen=True)
class Tool[A: ToolArguments]:
    """A command of fgraph an agent calls: its name, its arguments and the argv they build."""

    name: str
    description: str
    arguments: type[A]
    argv: Callable[[A], list[str]]


@dataclass(frozen=True)
class Command:
    """One run of fgraph: the directory it runs in and its argv."""

    directory: Path
    argv: list[str]


@dataclass(frozen=True)
class Ran:
    """What a run of fgraph left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def tool_listed(tool: Tool[Any]) -> dict[str, Any]:
    """The tool as tools/list gives it."""
    return {
        "name": tool.name,
        "description": tool.description,
        "inputSchema": tool.arguments.model_json_schema(),
    }


def command_of(tool: Tool[Any], arguments: Mapping[str, object]) -> Command:
    """The command a call of the tool runs, or ToolArgumentsError when its arguments are refused.

    A relative directory is kept as given, so it is read from the directory the server runs in.
    """
    try:
        given = tool.arguments.model_validate(arguments)
    except ValidationError as error:
        first = error.errors()[0]
        field = ".".join(str(part) for part in first["loc"])
        refused = REFUSED_ARGUMENTS.format(tool=tool.name, field=field, message=first["msg"])
        raise ToolArgumentsError(refused) from error
    return Command(Path(given.directory), tool.argv(given))


def ran_result(ran: Ran) -> dict[str, Any]:
    """The result of a call: the output of a run that exited 0, else its refusal as a tool error."""
    if ran.status != 0:
        lines = [line for line in ran.err.splitlines() if line.strip()]
        return refused_result(lines[-1] if lines else f"fgraph exited with status {ran.status}")
    texts = [ran.out, *([ran.err] if ran.err else [])]
    return {"content": [{"type": "text", "text": text} for text in texts]}


def refused_result(text: str) -> dict[str, Any]:
    """The result of a call that failed: the text as a tool error."""
    return {"content": [{"type": "text", "text": text}], "isError": True}
