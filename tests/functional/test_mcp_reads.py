"""The criterion of S-0158: an agent session lists the reads of fgraph as tools and calls them.

Run end to end as a real process, `fgraph mcp`, given on its stdin the messages of an agent session
shaped as those of tests/functional/test_mcp_status.py, on a record holding a started Story about a
term with a Task and a knowledge line.
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

XFAIL = pytest.mark.xfail(strict=True, reason="S-0158: fgraph mcp serves the status alone")

SCRIPT: Sequence[Sequence[str]] = (
    ("add", "term", "gate", "--means", "a check before a landing"),
    (
        "add",
        "story",
        "the story title",
        "--given",
        "a state",
        "--when",
        "an action",
        "--then",
        "another",
        "--about",
        "gate",
    ),
    ("add", "task", "a task title", "--parent", "S-0001", "--output", "changed: src/gate.py"),
    ("note", "S-0001", "--finding", "a thing learned", "--about", "gate"),
    ("start", "S-0001"),
)
READS = {
    "brief": ("brief", "S-0001", "--format", "json"),
    "show": ("show", "S-0001", "--format", "json"),
    "knowledge": ("knowledge", "--format", "json"),
    "about": ("about", "S-0001", "--format", "json"),
}
IDS = {"brief": 2, "show": 3, "knowledge": 4, "about": 5}
SHOW_MISSING = ("show", "S-0009", "--format", "json")
REQUIRED = {
    "brief": ["directory", "id"],
    "show": ["directory", "id"],
    "about": ["directory", "id"],
    "knowledge": ["directory"],
}


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
    for argv in SCRIPT:
        assert made.cli(*argv).status == 0
    return made


def call(id_: int, name: str, arguments: dict[str, object]) -> dict[str, object]:
    """A tools/call message of the id, with the arguments given."""
    return {
        "jsonrpc": "2.0",
        "id": id_,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


def messages(record: Path) -> str:
    """The messages of the session, one JSON a line, in the order sent."""
    directory = str(record)
    sent: Sequence[dict[str, Any]] = (
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
        call(2, "brief", {"directory": directory, "id": "S-0001"}),
        call(3, "show", {"directory": directory, "id": "S-0001"}),
        call(4, "knowledge", {"directory": directory}),
        call(5, "about", {"directory": directory, "id": "S-0001"}),
        call(6, "show", {"directory": directory, "id": "S-0009"}),
        call(7, "status", {"directory": directory}),
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


def listed(session: Outcome, name: str) -> dict[str, Any]:
    """The tool of that name as tools/list gives it, or an empty one."""
    tools = result(session, 1).get("tools", [])
    return next((tool for tool in tools if tool.get("name") == name), {})


@XFAIL
def test_the_five_reads_are_listed_as_tools(session: Outcome) -> None:
    names = [tool.get("name") for tool in result(session, 1).get("tools", [])]
    reads = {"status", "brief", "show", "knowledge", "about"}
    assert sorted(name for name in names if name in reads) == [
        "about",
        "brief",
        "knowledge",
        "show",
        "status",
    ]


@XFAIL
@pytest.mark.parametrize("name", list(REQUIRED))
def test_the_tool_requires_its_arguments(session: Outcome, name: str) -> None:
    assert listed(session, name).get("inputSchema", {}).get("required") == REQUIRED[name]


@XFAIL
@pytest.mark.parametrize("name", list(READS))
def test_the_call_gives_what_the_command_prints(
    session: Outcome, record: Record, name: str
) -> None:
    text = record.cli(*READS[name]).out
    assert result(session, IDS[name]).get("content") == [{"type": "text", "text": text}]


@XFAIL
@pytest.mark.parametrize("name", list(READS))
def test_the_call_is_one_text_and_no_error(session: Outcome, name: str) -> None:
    called = result(session, IDS[name])
    assert (called.get("isError", False), len(called.get("content", []))) == (False, 1)


@XFAIL
def test_a_missing_id_is_a_tool_error(session: Outcome) -> None:
    assert result(session, 6).get("isError") is True


@XFAIL
def test_a_missing_id_gives_the_one_line_of_the_refusal(session: Outcome, record: Record) -> None:
    refusal = record.cli(*SHOW_MISSING).err.splitlines()[-1]
    assert result(session, 6).get("content") == [{"type": "text", "text": refusal}]


@pytest.mark.parametrize("name", list(READS))
def test_the_command_of_the_read_exits_with_zero(record: Record, name: str) -> None:
    assert record.cli(*READS[name]).status == 0


def test_show_of_a_missing_id_exits_with_two(record: Record) -> None:
    assert record.cli(*SHOW_MISSING).status == 2


def test_the_status_tool_still_answers_with_one_text(session: Outcome) -> None:
    assert [item.get("type") for item in result(session, 7).get("content", [])] == ["text"]
