"""The lines of stdin answered on stdout: one reply a request, none a notification."""

import json

import pytest

from flowgraph.mcp.protocol import RunCommand
from flowgraph.mcp.reads import STATUS
from flowgraph.mcp.stdio import serve_lines
from flowgraph.mcp.tools import Command, Ran

pytestmark = pytest.mark.edge

PING = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
LIST = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
NOTIFICATION = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})


def run_command(command: Command) -> Ran:
    return Ran(0, "{}\n", "")


def served(lines: list[str]) -> tuple[list[str], int]:
    """What the lines were answered with, and the status once they end."""
    written: list[str] = []
    run: RunCommand = run_command
    status = serve_lines(lines, written.append, (STATUS,), run, "0.19.0")
    return written, status


def test_a_ping_and_a_list_write_two_lines() -> None:
    assert len(served([PING, LIST])[0]) == 2


def test_each_written_line_ends_with_a_newline() -> None:
    assert [line[-1] for line in served([PING, LIST])[0]] == ["\n", "\n"]


def test_a_notification_writes_nothing() -> None:
    assert served([NOTIFICATION])[0] == []


def test_a_blank_line_writes_nothing() -> None:
    assert served(["\n", "  \n"])[0] == []


def test_the_status_is_zero_once_the_lines_end() -> None:
    assert served([PING])[1] == 0
