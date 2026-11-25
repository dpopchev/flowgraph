"""The Model Context Protocol fgraph mcp answers, JSON-RPC 2.0, one message a line (F-0022).

A request is answered by one line, a notification by none; the methods are those of a server of
tools alone, initialize, ping, tools/list and tools/call; any other is refused as not found, so a
client that asks a newer method first, as Claude Code 2.1.331 asks server/discover, falls back to
initialize.
"""

import json
from collections.abc import Callable, Sequence
from typing import Any, Literal

from pydantic import BaseModel, StrictInt, StrictStr, ValidationError

from flowgraph.mcp.tools import (
    Command,
    Ran,
    Tool,
    ToolArgumentsError,
    command_of,
    ran_result,
    refused_result,
    tool_listed,
)

# The versions of the protocol answered, the newest first.
VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
NAME = "fgraph"
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Run one command of fgraph in its directory; what it left: a refusal of fgraph is its exit status
# and its line, not a raise.
RunCommand = Callable[[Command], Ran]


class Request(BaseModel):
    """A message of a client: a request when it holds an id, else a notification."""

    jsonrpc: Literal["2.0"]
    method: str
    id: StrictInt | StrictStr | None = None
    params: dict[str, Any] = {}


def replied(
    line: str, tools: Sequence[Tool[Any]], run_command: RunCommand, version: str
) -> str | None:
    """The one line that answers a line read, or None for a notification."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return _error(None, PARSE_ERROR, "Parse error")
    try:
        request = Request.model_validate(message)
    except ValidationError:
        return _error(None, INVALID_REQUEST, "Invalid Request")
    if "id" not in request.model_fields_set:
        return None
    id_ = request.id
    params = request.params
    match request.method:
        case "initialize":
            asked = params.get("protocolVersion")
            chosen = asked if asked in VERSIONS else VERSIONS[0]
            return _result(
                id_,
                {
                    "protocolVersion": chosen,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": NAME, "version": version},
                },
            )
        case "ping":
            return _result(id_, {})
        case "tools/list":
            return _result(id_, {"tools": [tool_listed(tool) for tool in tools]})
        case "tools/call":
            return _called(id_, params, tools, run_command)
        case _:
            return _error(id_, METHOD_NOT_FOUND, f"Method not found: {request.method}")


def _called(
    id_: int | str | None,
    params: dict[str, Any],
    tools: Sequence[Tool[Any]],
    run_command: RunCommand,
) -> str:
    """The reply to a call of a tool: its result, a tool error, or an error of the protocol."""
    name = params.get("name")
    tool = next((each for each in tools if each.name == name), None)
    if tool is None:
        return _error(id_, INVALID_PARAMS, f"Unknown tool: {name}")
    try:
        command = command_of(tool, params.get("arguments", {}))
    except ToolArgumentsError as refused:
        return _result(id_, refused_result(str(refused)))
    try:
        ran = run_command(command)
    except Exception as raised:  # the one boundary of a call: the server answers and goes on
        return _error(id_, INTERNAL_ERROR, f"{type(raised).__name__}: {raised}")
    return _result(id_, ran_result(ran))


def _error(id_: int | str | None, code: int, message: str) -> str:
    """The line of an error reply."""
    return json.dumps({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})


def _result(id_: int | str | None, result: dict[str, Any]) -> str:
    """The line of a result reply."""
    return json.dumps({"jsonrpc": "2.0", "id": id_, "result": result})
