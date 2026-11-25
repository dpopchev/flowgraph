"""The shell of fgraph mcp: it reads a message a line on stdin and writes each reply on stdout.

Each call is one run of fgraph in process, in the directory it names, given the effects main() of
src/flowgraph/cli.py gives run(), so one server writes main and the worktree of a work item alike
and a write takes the lock of its record as the command line does, the server holding none (F-0022).
"""

import importlib.metadata
import io
import os
from collections.abc import Callable, Iterable, Sequence
from contextlib import redirect_stderr
from functools import partial
from pathlib import Path
from typing import Any, Protocol, TextIO

from flowgraph.mcp.closing import CLOSING_TOOLS
from flowgraph.mcp.moves import MOVE_TOOLS
from flowgraph.mcp.protocol import RunCommand, replied
from flowgraph.mcp.reads import READ_TOOLS
from flowgraph.mcp.tools import Command, Ran, Tool

# Write text to a stream; what it returns is ignored, so a stream's write and a list's append fit.
Write = Callable[[str], object]

# Serve the tools of fgraph until the input closes; the exit status.
Serve = Callable[[], int]

SERVED = (*READ_TOOLS, *MOVE_TOOLS, *CLOSING_TOOLS)
NOT_A_DIRECTORY = (
    "fgraph: error: {directory} is not a directory: a call runs fgraph in the directory it names"
)


class Fgraph(Protocol):
    """run() of fgraph with every effect bound but its two streams."""

    def __call__(
        self, argv: Sequence[str], cwd: Path, *, write: Write, write_error: Write
    ) -> int: ...


def called(fgraph: Fgraph, command: Command) -> Ran:
    """Run the command through fgraph in its directory, taking what it wrote and what it refused.

    The parser of fgraph writes its refusal to sys.stderr and exits before run() is reached: that
    line is the refusal of the call, and the server goes on.
    """
    if not command.directory.is_dir():
        return Ran(2, "", NOT_A_DIRECTORY.format(directory=command.directory) + "\n")
    out: list[str] = []
    err = io.StringIO()
    with redirect_stderr(err):
        try:
            status = fgraph(
                command.argv, command.directory, write=out.append, write_error=err.write
            )
        except SystemExit as refused:
            status = refused.code if isinstance(refused.code, int) else 2
    return Ran(status, "".join(out), err.getvalue())


def serve_lines(
    lines: Iterable[str],
    write: Write,
    tools: Sequence[Tool[Any]],
    run_command: RunCommand,
    version: str,
) -> int:
    """Write the reply of each line read; 0 once the lines end."""
    for line in lines:
        if not line.strip():
            continue
        reply = replied(line, tools, run_command, version)
        if reply is not None:
            write(reply + "\n")
    return 0


def protocol_streams() -> tuple[TextIO, TextIO]:
    """Adapter: the protocol's own copies of stdin and stdout, the process left with none of them.

    fd 0 then reads /dev/null and fd 1 writes to stderr, so a check or a gate a call runs neither
    reads a message nor writes into the replies (S-0159).
    """
    protocol_in = os.fdopen(os.dup(0), "r", encoding="utf-8")
    protocol_out = os.fdopen(os.dup(1), "w", encoding="utf-8")
    nothing = os.open(os.devnull, os.O_RDONLY)
    os.dup2(nothing, 0)
    os.close(nothing)
    os.dup2(2, 1)
    return protocol_in, protocol_out


def serve_stdio(fgraph: Fgraph) -> int:
    """Serve SERVED on the streams of the protocol, each call a run of fgraph, until stdin closes.

    The streams are those protocol_streams() keeps: sys.stdin and sys.stdout are neither read nor
    written here, and sys.stdout, still fd 1, then writes to stderr.
    """
    protocol_in, protocol_out = protocol_streams()

    def write(text: str) -> None:
        protocol_out.write(text)
        protocol_out.flush()

    return serve_lines(
        protocol_in,
        write,
        SERVED,
        partial(called, fgraph),
        importlib.metadata.version("flowgraph"),
    )
