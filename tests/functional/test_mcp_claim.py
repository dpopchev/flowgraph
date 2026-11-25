"""The criterion of S-0165: an agent claims the first Backlog line that can start over fgraph mcp.

Run end to end as a real process, `fgraph mcp`, on a git repository with the development on and one
planned Story in Backlog: the tool start is called on main with no id, and the claim is committed on
main and handed to the agent; a second start with nothing left to start relays the one line that
fgraph start --agent prints. The identity of every commit comes from the environment and no git
config is read; every read of the server waits PATIENCE seconds at most.
"""

import contextlib
import json
import os
import selectors
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.functional

PATIENCE = 60
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
ADD_STORY = [
    *("add", "story", "Raise the claims of fgraph from 0 to 1"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = [
    *("add", "task", "a task title", "--parent", "S-0001"),
    *("--output", "changed: work.txt", "--check", "true"),
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


@dataclass(frozen=True)
class Project:
    """A git repository on main holding a record, and the environment every run is given there."""

    path: Path
    environ: dict[str, str]


def git(cwd: Path, environ: dict[str, str], *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=environ, check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def cli(project: Project, *argv: str) -> Outcome:
    """Run fgraph as a process in the project, with its environment."""
    done = subprocess.run(
        [sys.executable, "-m", "flowgraph.cli", *argv],
        cwd=project.path,
        env=project.environ,
        capture_output=True,
        text=True,
        timeout=PATIENCE,
    )
    return Outcome(done.returncode, done.stdout, done.stderr)


def last_line(outcome: Outcome) -> str:
    """The last line of the error output of the run; empty when there is none."""
    return (outcome.err.splitlines() or [""])[-1]


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Project:
    """A repository whose first commit turns the development on, a Story with one Task planned."""
    path = tmp_path_factory.mktemp("project")
    empty = path.parent / "gitconfig"
    empty.touch()
    environ = {
        **os.environ,
        **IDENTITY,
        "GIT_CONFIG_GLOBAL": str(empty),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    git(path, environ, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    (path / ".fgraph" / "config.toml").write_text("[development]\nenabled = true\n", "utf-8")
    git(path, environ, "add", ".fgraph/config.toml")
    git(path, environ, "commit", "--quiet", "--message", "chore: turn the development on")
    made = Project(path, environ)
    for argv in (ADD_STORY, ADD_TASK):
        assert cli(made, *argv).status == 0
    return made


def parsed(line: str) -> dict[str, Any]:
    """The JSON object of the line, or an empty one when it is none."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return {}
    return message if isinstance(message, dict) else {}


def text(reply: dict[str, Any]) -> str:
    """The text of the first content of the result of the reply; empty when there is none."""
    content = reply.get("result", {}).get("content") or [{}]
    return content[0].get("text", "")


class Session:
    """fgraph mcp run as a process in the project: each request one line written, one read."""

    def __init__(self, project: Project) -> None:
        self.process = subprocess.Popen(
            [sys.executable, "-m", "flowgraph.cli", "mcp"],
            cwd=project.path,
            env=project.environ,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.lines: list[str] = []
        self.requests = 0

    def send(self, message: dict[str, Any]) -> bool:
        """Write the message as one line; False when the server has exited and refuses it."""
        assert self.process.stdin is not None
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            return False
        return True

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Write a request with the next id; the reply read, or an empty one."""
        message = {"jsonrpc": "2.0", "id": self.requests, "method": method, "params": params}
        self.requests += 1
        return parsed(self.line()) if self.send(message) else {}

    def call(self, name: str, **arguments: str) -> dict[str, Any]:
        """The reply to a call of the tool with those arguments."""
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def line(self) -> str:
        """The next line the server writes within PATIENCE seconds, kept; empty without one."""
        assert self.process.stdout is not None
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            ready = selector.select(PATIENCE)
        read = self.process.stdout.readline() if ready else ""
        if read:
            self.lines.append(read)
        return read

    def close(self) -> Outcome:
        """Close the input of the server; its exit status and its error output once it exits."""
        assert self.process.stdin is not None and self.process.stderr is not None
        with contextlib.suppress(BrokenPipeError):
            self.process.stdin.close()
        status = self.process.wait(timeout=PATIENCE)
        return Outcome(status, "", self.process.stderr.read())


@pytest.fixture(scope="module")
def claims(project: Project) -> dict[str, Any]:
    """Each step of the session by its name: a reply, an outcome or a list, in the order run."""
    session = Session(project)
    step: dict[str, Any] = {}
    try:
        session.request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}})
        session.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        step["claimed"] = session.call("start", directory=str(project.path), agent="sonnet-a1")
        step["subjects"] = git(project.path, project.environ, "log", "--format=%s").splitlines()
        step["again"] = session.call("start", directory=str(project.path), agent="opus-b2")
        step["direct"] = cli(project, "start", "--agent", "opus-b2")
        step["shown"] = json.loads(cli(project, "show", "S-0001", "--format", "json").out)
        tools = session.request("tools/list", {}).get("result", {}).get("tools", [])
        step["listed"] = tools
        step["ended"] = session.close()
    finally:
        if session.process.poll() is None:
            session.process.kill()
        session.process.wait()
    return {**step, "lines": session.lines, "requests": session.requests}


def start_schema(claims: dict[str, Any]) -> dict[str, Any]:
    """The input schema of the tool start, as listed; empty when it is not listed."""
    for tool in claims["listed"]:
        if tool.get("name") == "start":
            return tool.get("inputSchema", {})
    return {}


def test_the_start_with_no_id_answers_started_s_0001(claims: dict[str, Any]) -> None:
    assert text(claims["claimed"]).partition("\n")[0] == "started S-0001"


def test_the_claim_is_committed_on_main_before_the_direct_start(claims: dict[str, Any]) -> None:
    assert "chore: start S-0001 in the record" in claims["subjects"]


def test_the_claim_hands_the_story_to_sonnet_a1(claims: dict[str, Any]) -> None:
    assert claims["shown"].get("agent") == "sonnet-a1"


def test_a_second_start_relays_the_line_of_the_command(claims: dict[str, Any]) -> None:
    content = claims["again"].get("result", {}).get("content")
    assert content == [{"type": "text", "text": last_line(claims["direct"])}]


def test_the_input_schema_of_start_requires_the_directory_alone(claims: dict[str, Any]) -> None:
    assert start_schema(claims).get("required") == ["directory"]


def test_every_line_of_stdout_is_a_reply(claims: dict[str, Any]) -> None:
    assert [parsed(line).get("jsonrpc") for line in claims["lines"]] == ["2.0"] * claims["requests"]


def test_the_server_exits_with_zero_when_its_input_closes(claims: dict[str, Any]) -> None:
    assert claims["ended"].status == 0
