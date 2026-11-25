"""The criterion of S-0159: an agent moves its work item and its Tasks through fgraph mcp.

Run end to end as a real process, `fgraph mcp`, on a git repository with the development on: the
start is called on main, the moves of a Task in the worktree of its Story, and each is written
there as the command line writes it. The identity of every commit comes from the environment and
no git config is read; every read of the server waits PATIENCE seconds at most.
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
XFAIL = pytest.mark.xfail(strict=True, reason="S-0159: fgraph mcp serves no move")
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
ADD_STORY = [
    *("add", "story", "Raise the moves of fgraph from 0 to 1"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASKS = (
    [
        *("add", "task", "a task title", "--parent", "S-0001"),
        *("--output", "changed: work.txt", "--check", "echo checked && test -f work.txt"),
    ],
    [
        *("add", "task", "another task title", "--parent", "S-0001"),
        *("--output", "changed: more.txt", "--check", "exit 3"),
    ],
)
LEAF = "S-0001-raise-the-moves-of"
MOVES = ["block", "complete", "hand", "note", "start", "unblock"]
ADD_SECOND = ["add", "story", "a second story", "--given", "a", "--when", "b", "--then", "c"]
REFUSAL = 'fgraph: error: T-0002 cannot complete: its check "exit 3" exited with status 3'


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
    """A repository whose first commit turns the development on, a Story with two Tasks planned."""
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
    for argv in (ADD_STORY, *ADD_TASKS):
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


def committed(project: Project, name: str, task: str) -> str:
    """Commit a file of that name in the worktree of S-0001; its sha, or no commit without one."""
    if not project.worktree.is_dir():
        return "no commit"
    (project.worktree / name).write_text(f"the work of {task}\n", encoding="utf-8")
    git(project.worktree, project.environ, "add", name)
    git(
        project.worktree,
        project.environ,
        "commit",
        "--quiet",
        "--message",
        f"feat: the work of {task}",
    )
    return git(project.worktree, project.environ, "rev-parse", "HEAD")


def in_worktree(project: Project, *args: str) -> str:
    """The output of the git command in the worktree of S-0001, or no worktree without one."""
    if not project.worktree.is_dir():
        return "no worktree"
    return git(project.worktree, project.environ, *args)


@pytest.fixture(scope="module")
def moves(project: Project) -> dict[str, Any]:
    """Each step of the session by its name: a reply, an outcome or a sha, in the order run."""
    session = Session(project)
    tree = str(project.worktree)
    step: dict[str, Any] = {}
    try:
        session.request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}})
        session.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        step["started"] = session.call(
            "start", directory=str(project.path), id="S-0001", agent="sonnet-a1"
        )
        step["written"] = cli(project, *ADD_SECOND)
        step["task"] = session.call("start", directory=tree, id="T-0001")
        step["noted"] = session.call(
            "note", directory=tree, id="S-0001", kind="progress", text="red: a test"
        )
        step["work"] = committed(project, "work.txt", "T-0001")
        step["completed"] = session.call(
            "complete", directory=tree, id="T-0001", commit=step["work"]
        )
        step["second"] = session.call("start", directory=tree, id="T-0002")
        step["more"] = committed(project, "more.txt", "T-0002")
        step["refused"] = session.call("complete", directory=tree, id="T-0002", commit=step["more"])
        step["after"] = in_worktree(project, "rev-parse", "HEAD")
        tools = session.request("tools/list", {}).get("result", {}).get("tools", [])
        step["listed"] = [tool.get("name") for tool in tools]
        step["ended"] = session.close()
    finally:
        if session.process.poll() is None:
            session.process.kill()
        session.process.wait()
    return {**step, "lines": session.lines, "requests": session.requests}


def text(reply: dict[str, Any]) -> str:
    """The text of the first content of the result of the reply; empty when there is none."""
    content = reply.get("result", {}).get("content") or [{}]
    return content[0].get("text", "")


def subjects(cwd: Path, environ: dict[str, str]) -> list[str]:
    """The subjects of git log in cwd, the newest first."""
    return git(cwd, environ, "log", "--format=%s").splitlines()


@XFAIL
def test_the_start_answers_started_s_0001(moves: dict[str, Any]) -> None:
    assert text(moves["started"]).partition("\n")[0] == "started S-0001"


@XFAIL
def test_the_start_of_the_task_answers_its_line(moves: dict[str, Any]) -> None:
    assert text(moves["task"]) == "started T-0001 of S-0001\n"


@XFAIL
def test_the_note_answers_noted_s_0001(moves: dict[str, Any]) -> None:
    assert text(moves["noted"]) == "noted S-0001\n"


@XFAIL
def test_the_complete_answers_its_line_at_the_commit(moves: dict[str, Any]) -> None:
    assert text(moves["completed"]) == f"completed T-0001 of S-0001 at {moves['work']}\n"


@XFAIL
def test_the_start_is_committed_on_main(moves: dict[str, Any], project: Project) -> None:
    assert "chore: start S-0001 in the record" in subjects(project.path, project.environ)


@XFAIL
def test_the_moves_of_the_tasks_are_committed_on_the_branch(
    moves: dict[str, Any], project: Project
) -> None:
    logged = in_worktree(project, "log", "--format=%s")
    chores = [subject for subject in logged.splitlines() if subject.startswith("chore:")]
    assert chores[:4] == [
        "chore: start T-0002 of S-0001 in the record",
        "chore: complete T-0001 of S-0001 in the record",
        "chore: note S-0001 in the record",
        "chore: start T-0001 of S-0001 in the record",
    ]


@XFAIL
def test_the_refused_complete_is_a_tool_error(moves: dict[str, Any]) -> None:
    assert moves["refused"].get("result", {}).get("isError") is True


@XFAIL
def test_the_refused_complete_holds_its_one_line(moves: dict[str, Any]) -> None:
    assert moves["refused"].get("result", {}).get("content") == [{"type": "text", "text": REFUSAL}]


@XFAIL
def test_the_refused_complete_commits_nothing(moves: dict[str, Any]) -> None:
    assert moves["after"] == moves["more"]


@XFAIL
def test_the_refused_complete_leaves_the_worktree_clean(
    moves: dict[str, Any], project: Project
) -> None:
    assert in_worktree(project, "status", "--porcelain") == ""


def test_every_line_of_stdout_is_a_reply(moves: dict[str, Any]) -> None:
    assert [parsed(line).get("jsonrpc") for line in moves["lines"]] == ["2.0"] * moves["requests"]


@XFAIL
def test_the_output_of_the_check_reaches_the_stderr_of_the_server(moves: dict[str, Any]) -> None:
    assert "checked" in moves["ended"].err


@XFAIL
def test_the_moves_are_listed(moves: dict[str, Any]) -> None:
    assert sorted(set(moves["listed"]) & set(MOVES)) == MOVES


def test_the_server_exits_with_zero_when_its_input_closes(moves: dict[str, Any]) -> None:
    assert moves["ended"].status == 0


def test_a_write_on_main_while_the_server_runs_is_not_refused(moves: dict[str, Any]) -> None:
    assert moves["written"].status == 0


def test_main_holds_no_commit_of_a_move_of_a_task(moves: dict[str, Any], project: Project) -> None:
    assert "chore: start T-0001 of S-0001 in the record" not in subjects(
        project.path, project.environ
    )
