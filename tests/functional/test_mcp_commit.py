"""The criterion of S-0164: an agent commits the work of its started Task through fgraph mcp.

Run end to end as a real process, `fgraph mcp`, on a git repository with the development on: a
Story is started on main, its Task is started in the worktree of the Story, and the tool commit is
called there. Its reply is the line fgraph commit prints, or its one line of refusal as a tool
error. The identity of every commit comes from the environment and no git config is read; every
read of the server waits PATIENCE seconds at most.
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
    *("add", "story", "Raise the commits of fgraph from 0 to 1"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = [
    *("add", "task", "a task title", "--parent", "S-0001"),
    *("--output", "changed: work.txt", "--check", "test -f work.txt"),
]
LEAF = "S-0001-raise-the-commits-of"
REFUSAL = (
    "fgraph: error: T-0001 cannot commit: its brief does not name other.txt -- "
    "nothing is committed; take each back or have the brief name it"
)


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

    @property
    def worktree(self) -> Path:
        """The worktree of S-0001, beside the project."""
        return self.path.parent / f"{self.path.name}.worktrees" / LEAF


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


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Project:
    """A repository whose first commit turns the development on, a Story with its Task planned."""
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


def text(reply: dict[str, Any]) -> str:
    """The text of the first content of the result of the reply; empty when there is none."""
    content = reply.get("result", {}).get("content") or [{}]
    return content[0].get("text", "")


def head(where: Path, environ: dict[str, str]) -> str:
    """The sha of HEAD in the directory, or no worktree when the directory is not there."""
    if not where.is_dir():
        return "no worktree"
    return git(where, environ, "rev-parse", "HEAD")


@pytest.fixture(scope="module")
def commits(project: Project) -> dict[str, Any]:
    """Each step of the session by its name: a reply, an outcome or a sha, in the order run."""
    session = Session(project)
    tree = str(project.worktree)
    step: dict[str, Any] = {}
    try:
        session.request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}})
        session.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        session.call("start", directory=str(project.path), id="S-0001", agent="sonnet-a1")
        session.call("start", directory=tree, id="T-0001")
        if project.worktree.is_dir():
            (project.worktree / "work.txt").write_text("the work of T-0001\n", encoding="utf-8")
            (project.worktree / "other.txt").write_text("not named\n", encoding="utf-8")
        before = head(project.worktree, project.environ)
        step["refused"] = session.call(
            "commit", directory=tree, id="T-0001", message="feat: the work of T-0001"
        )
        step["after"] = head(project.worktree, project.environ)
        if project.worktree.is_dir():
            (project.worktree / "other.txt").unlink()
        step["committed"] = session.call(
            "commit", directory=tree, id="T-0001", message="feat: the work of T-0001"
        )
        step["at"] = head(project.worktree, project.environ)
        tools = session.request("tools/list", {}).get("result", {}).get("tools", [])
        step["listed"] = [tool.get("name") for tool in tools]
        schema = next((tool for tool in tools if tool.get("name") == "commit"), {})
        step["required"] = sorted(schema.get("inputSchema", {}).get("required", []))
        step["ended"] = session.close()
    finally:
        if session.process.poll() is None:
            session.process.kill()
        session.process.wait()
    return {**step, "before": before, "lines": session.lines, "requests": session.requests}


def test_the_refused_commit_holds_its_one_line(commits: dict[str, Any]) -> None:
    assert commits["refused"].get("result", {}).get("content") == [
        {"type": "text", "text": REFUSAL}
    ]


def test_the_refused_commit_is_a_tool_error(commits: dict[str, Any]) -> None:
    assert commits["refused"].get("result", {}).get("isError") is True


def test_the_commit_answers_its_line_at_its_sha(commits: dict[str, Any]) -> None:
    assert text(commits["committed"]) == f"committed T-0001 of S-0001 at {commits['at']}\n"


def test_the_commit_has_the_subject_with_the_ids(commits: dict[str, Any], project: Project) -> None:
    subject = git(project.worktree, project.environ, "log", "-1", "--format=%s")
    assert subject == "feat: the work of T-0001 (S-0001, T-0001)"


def test_the_commit_holds_the_named_file_alone(commits: dict[str, Any], project: Project) -> None:
    names = git(project.worktree, project.environ, "show", "--name-only", "--format=", "HEAD")
    assert names.splitlines() == ["work.txt"]


def test_the_worktree_is_left_clean(commits: dict[str, Any], project: Project) -> None:
    assert git(project.worktree, project.environ, "status", "--porcelain") == ""


def test_the_commit_is_listed(commits: dict[str, Any]) -> None:
    assert "commit" in commits["listed"]


def test_the_commit_requires_its_directory_id_and_message(commits: dict[str, Any]) -> None:
    assert commits["required"] == ["directory", "id", "message"]


def test_a_refusal_commits_nothing(commits: dict[str, Any]) -> None:
    assert commits["after"] == commits["before"]


def test_every_line_of_stdout_is_a_reply(commits: dict[str, Any]) -> None:
    assert [parsed(line).get("jsonrpc") for line in commits["lines"]] == ["2.0"] * commits[
        "requests"
    ]


def test_the_server_exits_with_zero_when_its_input_closes(commits: dict[str, Any]) -> None:
    assert commits["ended"].status == 0
