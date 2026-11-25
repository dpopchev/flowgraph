"""The criterion of S-0160: an agent lands its work item and keeps the answer of its closing.

Run end to end as a real process, `fgraph mcp`, on a git repository with the development on, a gate
that prints and a started Story whose one Task is completed: the tools land and verify are called
on main and leave the Story as the commands leave it. The identity of every commit comes from the
environment and no git config is read; every process run waits 60 seconds at most.
"""

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.functional

IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
LEAF = "S-0001-raise-the-landings-of"
HELD = (
    "fgraph: error: S-0001 cannot land: development.approver = developer, the landing waits for "
    "the developer -- run fgraph land S-0001 --approved once the developer approves it"
)


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


@dataclass(frozen=True)
class Project:
    """A git repository on main holding a record, its environment and the session run on it."""

    path: Path
    environ: dict[str, str]

    @property
    def worktree(self) -> Path:
        """The worktree of S-0001, beside the project."""
        return self.path.parent / f"{self.path.name}.worktrees" / LEAF


def git(cwd: Path, environ: dict[str, str], *args: str, check: bool = True) -> str:
    """The output of the git command run in cwd, stripped."""
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=environ, check=check, capture_output=True, text=True
    )
    return done.stdout.strip()


def cli(project: Project, *argv: str, cwd: Path | None = None) -> Outcome:
    """Run fgraph as a process in the project, or in cwd, with its environment."""
    done = subprocess.run(
        [sys.executable, "-m", "flowgraph.cli", *argv],
        cwd=cwd or project.path,
        env=project.environ,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return Outcome(done.returncode, done.stdout, done.stderr)


def repository(base: Path, approver: str) -> Project:
    """A repository holding a started Story whose one Task is completed on its branch."""
    path = base / "project"
    path.mkdir()
    empty = base / "gitconfig"
    empty.touch()
    environ = {
        **os.environ,
        **IDENTITY,
        "GIT_CONFIG_GLOBAL": str(empty),
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    git(path, environ, "init", "--quiet", "--initial-branch", "main")
    (path / ".fgraph").mkdir()
    config = f'[development]\nenabled = true\ngate = "echo gated"\napprover = "{approver}"\n'
    (path / ".fgraph" / "config.toml").write_text(config, "utf-8")
    git(path, environ, "add", ".fgraph/config.toml")
    git(path, environ, "commit", "--quiet", "--message", "chore: turn the development on")
    made = Project(path, environ)
    story = ["add", "story", "Raise the landings of fgraph from 0 to 1"]
    story += ["--given", "a state", "--when", "an action", "--then", "another"]
    task = ["add", "task", "a task title", "--parent", "S-0001"]
    task += ["--output", "changed: work.txt", "--check", "test -f work.txt"]
    for argv in (story, task, ["start", "S-0001"]):
        assert cli(made, *argv).status == 0
    assert cli(made, "start", "T-0001", cwd=made.worktree).status == 0
    (made.worktree / "work.txt").write_text("the work of T-0001\n", "utf-8")
    git(made.worktree, environ, "add", "work.txt")
    git(made.worktree, environ, "commit", "--quiet", "--message", "feat: the work of T-0001")
    sha = git(made.worktree, environ, "rev-parse", "HEAD")
    assert cli(made, "complete", "T-0001", "--commit", sha, cwd=made.worktree).status == 0
    return made


def messages(project: Path) -> str:
    """The messages an agent sends, one JSON a line: the handshake, the list, land and verify."""
    directory = str(project)
    calls = (
        ("land", {"directory": directory, "id": "S-0001", "message": "feat: land S-0001"}),
        (
            "verify",
            {"directory": directory, "id": "S-0001", "answer": "yes", "text": "it holds"},
        ),
    )
    sent: list[dict[str, Any]] = [
        {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {}},
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
    ]
    for number, (name, arguments) in enumerate(calls, start=2):
        params = {"name": name, "arguments": arguments}
        sent.append({"jsonrpc": "2.0", "id": number, "method": "tools/call", "params": params})
    return "".join(json.dumps(message) + "\n" for message in sent)


@dataclass(frozen=True)
class Run:
    """A repository and what its session of the server printed."""

    project: Project
    session: Outcome


def session_of(base: Path, approver: str) -> Run:
    """Build the repository and run the server on it, its input written whole and closed."""
    made = repository(base, approver)
    done = subprocess.run(
        [sys.executable, "-m", "flowgraph.cli", "mcp"],
        cwd=made.path,
        env=made.environ,
        input=messages(made.path),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return Run(made, Outcome(done.returncode, done.stdout, done.stderr))


@pytest.fixture(scope="module")
def agent(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """The repository whose approver is the agent, and its session."""
    return session_of(tmp_path_factory.mktemp("agent"), "agent")


@pytest.fixture(scope="module")
def developer(tmp_path_factory: pytest.TempPathFactory) -> Run:
    """The repository whose approver is the developer, and its session."""
    return session_of(tmp_path_factory.mktemp("developer"), "developer")


def parsed(line: str) -> dict[str, Any]:
    """The JSON object of the line, or an empty one when it is none."""
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        return {}
    return message if isinstance(message, dict) else {}


def replies(run: Run) -> dict[Any, dict[str, Any]]:
    """The replies of the server by the id they answer."""
    return {message.get("id"): message for message in map(parsed, run.session.out.splitlines())}


def result(run: Run, id_: Any) -> dict[str, Any]:
    """The result of the reply under that id, or an empty one."""
    return replies(run).get(id_, {}).get("result", {})


def text(run: Run, id_: Any) -> str:
    """The text of the first content of the result under that id; empty when there is none."""
    content = result(run, id_).get("content") or [{}]
    return content[0].get("text", "")


def items(node: Any) -> Iterator[dict[str, Any]]:
    """Each dict of the JSON tree that holds an id."""
    if isinstance(node, dict):
        if "id" in node:
            yield node
        for value in node.values():
            yield from items(value)
    elif isinstance(node, list):
        for value in node:
            yield from items(value)


def story(run: Run) -> dict[str, Any]:
    """S-0001 as fgraph status --format json prints it on main."""
    printed = json.loads(cli(run.project, "status", "--format", "json").out)
    return next(item for item in items(printed) if item["id"] == "S-0001" and "state" in item)


def rev(run: Run, name: str) -> str:
    """The sha of the commit git knows by that name on main; empty when it knows none."""
    return git(
        run.project.path,
        run.project.environ,
        "rev-parse",
        "--verify",
        "--quiet",
        f"{name}^{{commit}}",
        check=False,
    )


def test_the_land_answers_its_line(agent: Run) -> None:
    assert text(agent, 2).startswith("landed S-0001 at")


def test_the_verify_answers_its_line(agent: Run) -> None:
    assert text(agent, 3) == "verified S-0001\n"


def test_the_story_is_completed_on_main(agent: Run) -> None:
    assert story(agent)["state"] == "completed"


def test_the_story_is_completed_at_the_merge_commit(agent: Run) -> None:
    project = agent.project
    merge = git(
        project.path, project.environ, "log", "--format=%H", "--grep", "^feat: land S-0001$"
    )
    assert [rev(agent, str(story(agent)["commit"]))] == merge.splitlines()


def test_the_answer_and_its_text_are_kept(agent: Run) -> None:
    shown = cli(agent.project, "show", "S-0001").out
    kept = [
        (words[1], words[3:])
        for words in (line.split() for line in shown.splitlines())
        if words[:1] == ["verified"]
    ]
    assert kept == [("yes", ["it", "holds"])]


def test_every_line_of_stdout_is_a_reply(agent: Run) -> None:
    assert [parsed(line).get("jsonrpc") for line in agent.session.out.splitlines()] == ["2.0"] * 4


def test_the_gate_printed_on_the_stderr_of_the_server(agent: Run) -> None:
    assert "gated" in agent.session.err


def test_a_landing_waiting_for_the_developer_is_a_tool_error(developer: Run) -> None:
    assert result(developer, 2).get("isError") is True


def test_a_landing_waiting_for_the_developer_holds_its_one_line(developer: Run) -> None:
    assert result(developer, 2).get("content") == [{"type": "text", "text": HELD}]


def test_a_landing_waiting_for_the_developer_leaves_the_story_started(developer: Run) -> None:
    assert story(developer)["state"] == "started"


def test_no_tool_takes_the_approval_of_a_landing(agent: Run) -> None:
    tools = result(agent, 1).get("tools", [])
    assert [tool["name"] for tool in tools if "approved" in tool["inputSchema"]["properties"]] == []
