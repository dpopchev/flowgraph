"""The reply of fgraph mcp to a line of JSON-RPC 2.0."""

import json
from pathlib import Path
from typing import Any

import pytest

from flowgraph.mcp.protocol import replied
from flowgraph.mcp.reads import STATUS
from flowgraph.mcp.tools import Command, Ran

pytestmark = pytest.mark.view

VERSION = "0.19.0"
PROBE = "server-discover-probe-1"
STATUS_COMMAND = Command(Path("/src/project"), ["status", "--format", "json"])
EMPTY = Ran(0, "{}\n", "")
CALL = {"name": "status", "arguments": {"directory": "/src/project"}}


def initialize(version: object = "2025-11-25") -> dict[str, Any]:
    """The initialize request with id 0, asking that version, or none when it is None."""
    params = {} if version is None else {"protocolVersion": version}
    return {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": params}


def request(method: str, params: object = None, id_: object = 1) -> dict[str, Any]:
    """A request of that method under that id."""
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        message["params"] = params
    return message


def reply(
    message: object,
    ran: Ran | Exception = EMPTY,
    run: list[Command] | None = None,
) -> str | None:
    """The reply to the message, the commands run appended to `run`."""
    kept = [] if run is None else run

    def run_command(command: Command) -> Ran:
        kept.append(command)
        if isinstance(ran, Exception):
            raise ran
        return ran

    return replied(json.dumps(message), (STATUS,), run_command, VERSION)


def answer(
    message: object,
    ran: Ran | Exception = EMPTY,
    run: list[Command] | None = None,
) -> dict[str, Any]:
    """The reply to the message as a JSON object."""
    return json.loads(reply(message, ran, run) or "null")


def result(message: object, **given: Any) -> dict[str, Any]:
    """The result of the reply to the message."""
    return answer(message, **given).get("result", {})


def error(message: object, **given: Any) -> dict[str, Any]:
    """The error of the reply to the message."""
    return answer(message, **given).get("error", {})


def never(command: Command) -> Ran:
    raise AssertionError(f"run_command was called with {command}")


def test_initialize_answers_the_version_asked() -> None:
    assert result(initialize("2025-11-25"))["protocolVersion"] == "2025-11-25"


def test_the_reply_holds_the_id_of_the_request() -> None:
    assert answer(initialize())["id"] == 0


@pytest.mark.parametrize("asked", ["2025-06-18", "2024-11-05"])
def test_initialize_answers_an_older_version_it_holds(asked: str) -> None:
    assert result(initialize(asked))["protocolVersion"] == asked


@pytest.mark.parametrize("asked", ["1999-01-01", None])
def test_initialize_answers_the_newest_for_a_version_it_does_not_hold(asked: str | None) -> None:
    assert result(initialize(asked))["protocolVersion"] == "2025-11-25"


def test_the_capabilities_are_the_tools() -> None:
    assert result(initialize())["capabilities"] == {"tools": {}}


def test_the_server_is_named_fgraph_with_its_version() -> None:
    assert result(initialize())["serverInfo"] == {"name": "fgraph", "version": VERSION}


@pytest.mark.parametrize(
    "message",
    [
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "method": "an/unknown"},
    ],
)
def test_a_message_with_no_id_is_given_no_reply(message: dict[str, Any]) -> None:
    assert reply(message) is None


def test_ping_gives_an_empty_result() -> None:
    assert result(request("ping")) == {}


def test_tools_list_gives_the_names_of_the_tools() -> None:
    assert [tool["name"] for tool in result(request("tools/list"))["tools"]] == ["status"]


def test_a_call_gives_the_output_of_the_run() -> None:
    assert result(request("tools/call", CALL)) == {"content": [{"type": "text", "text": "{}\n"}]}


def test_a_call_runs_the_command_of_the_tool() -> None:
    run: list[Command] = []
    reply(request("tools/call", CALL), run=run)
    assert run == [STATUS_COMMAND]


def test_a_run_that_exits_with_two_is_a_tool_error() -> None:
    ran = Ran(2, "", "fgraph: error: no record\n")
    assert result(request("tools/call", CALL), ran=ran)["isError"] is True


def test_an_unknown_tool_is_the_error_invalid_params() -> None:
    assert error(request("tools/call", {"name": "nope"})) == {
        "code": -32602,
        "message": "Unknown tool: nope",
    }


def test_an_unknown_tool_runs_nothing() -> None:
    run: list[Command] = []
    reply(request("tools/call", {"name": "nope"}), run=run)
    assert run == []


def test_refused_arguments_are_a_tool_error() -> None:
    assert result(request("tools/call", {"name": "status", "arguments": {}})) == {
        "content": [
            {
                "type": "text",
                "text": "the arguments of status are refused: directory: Field required",
            }
        ],
        "isError": True,
    }


def test_refused_arguments_run_nothing() -> None:
    run: list[Command] = []
    reply(request("tools/call", {"name": "status"}), run=run)
    assert run == []


def test_a_run_that_raised_is_the_error_internal_under_the_id_of_the_request() -> None:
    assert answer(request("tools/call", CALL, id_=7), ran=RuntimeError("boom")) == {
        "jsonrpc": "2.0",
        "id": 7,
        "error": {"code": -32603, "message": "RuntimeError: boom"},
    }


def test_server_discover_is_not_found_under_its_string_id() -> None:
    assert answer(request("server/discover", {}, id_=PROBE)) == {
        "jsonrpc": "2.0",
        "id": PROBE,
        "error": {"code": -32601, "message": "Method not found: server/discover"},
    }


def test_a_line_that_is_no_json_is_a_parse_error_with_no_id() -> None:
    assert json.loads(replied("{not json", (STATUS,), never, VERSION) or "") == {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32700, "message": "Parse error"},
    }


@pytest.mark.parametrize(
    "message",
    [
        [1, 2],
        {"jsonrpc": "1.0", "id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": True, "method": "ping"},
        {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": [1]},
    ],
)
def test_a_line_that_is_no_message_is_an_invalid_request_with_no_id(message: object) -> None:
    reply_ = answer(message)
    assert (reply_["error"]["code"], reply_["id"]) == (-32600, None)


def test_the_reply_of_a_text_with_a_newline_is_one_line() -> None:
    assert "\n" not in (reply(request("tools/call", CALL), ran=Ran(0, "a\nb\n", "")) or "")
