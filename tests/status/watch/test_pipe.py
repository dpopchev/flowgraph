"""The frames of fgraph watch written to a pipe: each one reaches it as it is written.

Run as a process of its own, its stdout a pipe, since the buffer of a stream is what is under
test; the second frame is a minute away, so a frame held in the buffer is not read in time.
"""

import selectors
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = pytest.mark.edge

# The seconds the first frame is waited for, well under the interval to the second.
PATIENCE = 10


@pytest.fixture
def watching(tmp_path: Path) -> Iterator[subprocess.Popen[str]]:
    """fgraph watch of an empty record, every minute for two frames, its stdout a pipe."""
    (tmp_path / ".fgraph").mkdir()
    argv = [sys.executable, "-m", "flowgraph.cli", "watch", "-n", "60", "--count", "2"]
    process = subprocess.Popen(argv, cwd=tmp_path, stdout=subprocess.PIPE, text=True)
    yield process
    process.kill()
    process.wait()


def first_line(process: subprocess.Popen[str]) -> str:
    """The first line the process writes to its pipe within PATIENCE seconds; empty without one."""
    assert process.stdout is not None
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        ready = selector.select(PATIENCE)
    return process.stdout.readline() if ready else ""


def test_the_first_frame_of_watch_reaches_a_pipe_before_the_second_is_due(
    watching: subprocess.Popen[str],
) -> None:
    assert first_line(watching) == "backlog (0)\n"
