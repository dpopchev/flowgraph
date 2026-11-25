"""The criterion of S-0157: an agent session lists the tool status of fgraph and calls it.

Run end to end as a real process, `fgraph mcp`, given on its stdin the messages Claude Code 2.1.331
sent on 2026-11-25, in that order and shapes, and then closed.
"""

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.functional

PROBE = "server-discover-probe-1"
ADD_STORY = [
    *("add", "story", "Raise the tools of fgraph from 0 to 1"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def environment(base: Path) -> dict[str, str]:
    """The environment of every run: no git configuration of the developer is read."""
    empty = base / "gitconfig"
    empty.write_text("")
    return {**os.environ, "GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1"}


def cli(record: Path, environ: dict[str, str], *argv: str) -> Outcome:
    """Run fgraph as a process in the record, with that environment."""
    done = subprocess.run(
        [sys.executable, "-m", "flowgraph.cli", *argv],
        cwd=record,
        env=environ,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return Outcome(done.returncode, done.stdout, done.stderr)


@dataclass(frozen=True)
class Record:
    """A directory holding a record, and the environment fgraph is run with there."""

    path: Path
    environ: dict[str, str]

    def cli(self, *argv: str) -> Outcome:
        return cli(self.path, self.environ, *argv)


@pytest.fixture(scope="module")
def record(tmp_path_factory: pytest.TempPathFactory) -> Record:
    path = tmp_path_factory.mktemp("project")
    (path / ".fgraph").mkdir()
    made = Record(path, environment(tmp_path_factory.mktemp("environment")))
    assert made.cli(*ADD_STORY).status == 0
    return made


def messages(record: Path) -> str:
    """The messages Claude Code sends, one JSON a line, in the order it sends them."""
    sent: Sequence[dict[str, Any]] = (
        {"jsonrpc": "2.0", "id": PROBE, "method": "server/discover", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "a-client", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "status", "arguments": {"directory": str(record)}},
        },
    )
    return "".join(json.dumps(message) + "\n" for message in sent)


@pytest.fixture(scope="module")
def session(record: Record) -> Outcome:
    done = subprocess.run(
        [sys.executable, "-m", "flowgraph.cli", "mcp"],
        cwd=record.path,
        env=record.environ,
        input=messages(record.path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return Outcome(done.returncode, done.stdout, done.stderr)


def parsed(line: str) -> dict[str, Any]:
    """The JSON object of the line, or an empty one when it is none."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return {}
    return message if isinstance(message, dict) else {}


def replies(session: Outcome) -> dict[Any, dict[str, Any]]:
    """The replies of the server by the id they answer."""
    return {message.get("id"): message for message in map(parsed, session.out.splitlines())}


def result(session: Outcome, id_: Any) -> dict[str, Any]:
    """The result of the reply under that id, or an empty one."""
    return replies(session).get(id_, {}).get("result", {})


def status_tool(session: Outcome) -> dict[str, Any]:
    """The tool status as listed."""
    return next(tool for tool in result(session, 1).get("tools", []) if tool["name"] == "status")


def test_the_status_of_the_record_exits_with_zero(record: Record) -> None:
    assert record.cli("status", "--format", "json").status == 0


def test_the_status_of_the_record_holds_buckets(record: Record) -> None:
    assert "buckets" in json.loads(record.cli("status", "--format", "json").out)


def test_server_discover_is_answered_not_found(session: Outcome) -> None:
    assert replies(session).get(PROBE, {}).get("error", {}).get("code") == -32601


def test_initialize_answers_the_version_asked(session: Outcome) -> None:
    assert result(session, 0).get("protocolVersion") == "2025-11-25"


def test_initialize_names_the_server_fgraph(session: Outcome) -> None:
    assert result(session, 0).get("serverInfo", {}).get("name") == "fgraph"


def test_initialize_gives_the_capability_tools(session: Outcome) -> None:
    assert "tools" in result(session, 0).get("capabilities", {})


def test_the_notification_is_given_no_reply(session: Outcome) -> None:
    assert sorted(replies(session), key=str) == [0, 1, 2, PROBE]


def test_the_tool_status_is_listed(session: Outcome) -> None:
    listed = [
        tool["name"] for tool in result(session, 1).get("tools", []) if tool["name"] == "status"
    ]
    assert listed == ["status"]


def test_the_tool_status_requires_directory(session: Outcome) -> None:
    assert status_tool(session)["inputSchema"]["required"] == ["directory"]


def test_the_call_gives_what_status_prints(session: Outcome, record: Record) -> None:
    text = record.cli("status", "--format", "json").out
    assert result(session, 2).get("content") == [{"type": "text", "text": text}]


def test_the_call_is_one_text_and_no_error(session: Outcome) -> None:
    called = result(session, 2)
    assert (called.get("isError", False), len(called.get("content", []))) == (False, 1)


def test_stdout_holds_the_four_replies_alone(session: Outcome) -> None:
    assert [parsed(line).get("jsonrpc") for line in session.out.splitlines()] == ["2.0"] * 4


def test_the_server_ends_with_zero_when_its_input_closes(session: Outcome) -> None:
    assert session.status == 0
