"""The gate of a landing: the one command of the record a landing runs before main moves.

`[development] gate` of the configuration names it. A landing runs it through the shell at the
top of the work tree of main while the merge of the branch is held there, so it sees the tree
main will have, and is refused when it exits with another status than 0.
"""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import assert_never

from flowgraph.record import DEVELOPMENT_GATE, Gate, Gated, Ungated

# Run a command line through the shell in a directory; the status it exits with.
RunGate = Callable[[str, Path], int]


class GateError(Exception):
    """A landing its gate refuses; the message names the command and the status it exited with."""


def check_gate(item: str, gate: Gate, top: Path, run_gate: RunGate) -> None:
    """Run the gate, when the record names one, at the top of the work tree of main.

    Raises GateError naming the key, the command as the file writes it and its status when it
    exits with another status than 0.
    """
    match gate:
        case Ungated():
            return
        case Gated(command):
            status = run_gate(command, top)
            if status != 0:
                written = f"{DEVELOPMENT_GATE} = {json.dumps(command)}"
                raise GateError(f"{item} cannot land: {written} exited with status {status}")
        case _ as unreachable:
            assert_never(unreachable)


def run_gate(command: str, directory: Path) -> int:
    """Adapter: run the command line through the shell in the directory; its exit status.

    Its output and its error output are those of the process, written as the command writes
    them: nothing is captured.
    """
    return subprocess.run(command, shell=True, cwd=directory, check=False).returncode
