"""One call of a tool as a run of fgraph in its directory: what it wrote and how it refused."""

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Never

import pytest

from flowgraph.mcp.stdio import NOT_A_DIRECTORY, Write, called
from flowgraph.mcp.tools import Command, Ran

pytestmark = pytest.mark.edge


def fake(argv: Sequence[str], cwd: Path, *, write: Write, write_error: Write) -> int:
    """A fgraph that writes an output and a warning and exits 0."""
    write("out\n")
    write_error("warning\n")
    return 0


def usage(argv: Sequence[str], cwd: Path, *, write: Write, write_error: Write) -> Never:
    """A fgraph whose parser refuses an option, writing to sys.stderr and exiting 2."""
    print("usage: fgraph", file=sys.stderr)
    print("fgraph: error: unrecognized arguments: --x", file=sys.stderr)
    raise SystemExit(2)


def refusing(argv: Sequence[str], cwd: Path, *, write: Write, write_error: Write) -> int:
    """A fgraph that exits 2."""
    return 2


def never(argv: Sequence[str], cwd: Path, *, write: Write, write_error: Write) -> Never:
    raise AssertionError("fgraph was run")


def test_a_run_gives_its_output_and_its_error_output(tmp_path: Path) -> None:
    assert called(fake, Command(tmp_path, ["status"])) == Ran(0, "out\n", "warning\n")


def test_fgraph_is_given_the_argv_and_the_directory(tmp_path: Path) -> None:
    given: list[tuple[Sequence[str], Path]] = []

    def recording(argv: Sequence[str], cwd: Path, *, write: Write, write_error: Write) -> int:
        given.append((argv, cwd))
        return 0

    called(recording, Command(tmp_path, ["status"]))
    assert given == [(["status"], tmp_path)]


def test_a_refusal_of_the_parser_is_the_status_two(tmp_path: Path) -> None:
    assert called(usage, Command(tmp_path, ["status"])).status == 2


def test_a_refusal_of_the_parser_is_its_line_of_error_output(tmp_path: Path) -> None:
    ran = called(usage, Command(tmp_path, ["status"]))
    assert ran.err.endswith("fgraph: error: unrecognized arguments: --x\n")


def test_a_run_that_returns_two_is_the_status_two(tmp_path: Path) -> None:
    assert called(refusing, Command(tmp_path, ["status"])).status == 2


def test_a_directory_that_is_none_is_refused(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert called(never, Command(missing, ["status"])) == Ran(
        2, "", NOT_A_DIRECTORY.format(directory=missing) + "\n"
    )
