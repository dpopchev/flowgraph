"""The streams of the protocol, kept from a command a call runs: it reads nothing, writes aside.

Run in a child process, since protocol_streams replaces fd 0 and fd 1 of the process it runs in.
"""

import subprocess
import sys

import pytest

pytestmark = pytest.mark.edge

CHILD = "\n".join(
    [
        "from flowgraph.mcp.stdio import protocol_streams",
        "import subprocess",
        "protocol_in, protocol_out = protocol_streams()",
        "subprocess.run('echo aside; cat', shell=True)",
        "protocol_out.write(protocol_in.readline())",
        "protocol_out.flush()",
    ]
)


@pytest.fixture(scope="module")
def child() -> subprocess.CompletedProcess[str]:
    """The child given a message on stdin, running a command that reads fd 0 and writes fd 1."""
    return subprocess.run(
        [sys.executable, "-c", CHILD],
        input="a message\n",
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_the_line_read_reaches_the_protocol_and_nothing_else_its_stdout(
    child: subprocess.CompletedProcess[str],
) -> None:
    assert child.stdout == "a message\n"


def test_what_the_command_writes_reaches_stderr(child: subprocess.CompletedProcess[str]) -> None:
    assert "aside" in child.stderr


def test_the_child_exits_with_zero(child: subprocess.CompletedProcess[str]) -> None:
    assert child.returncode == 0
