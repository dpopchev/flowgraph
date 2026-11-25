"""The run of fgraph mcp: it serves through the serve it is given and needs no record.

Run through `run` in a directory that holds no record: the store and git are never opened.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Never

import pytest

from flowgraph.cli import run

pytestmark = pytest.mark.functional


def never(*_: object) -> Never:
    """The store or the git work tree of a record, which fgraph mcp never opens."""
    raise AssertionError("fgraph mcp opens no record")


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], serve: Callable[[], int] | None = None) -> Outcome:
    """Run the command in a directory that holds no record, given that serve when there is one."""
    out: list[str] = []
    err: list[str] = []
    effects: dict[str, Any] = {} if serve is None else {"serve": serve}
    status = run(
        argv,
        Path("/work"),
        lambda _: False,
        out.append,
        err.append,
        open_store=never,
        open_git=never,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
        **effects,
    )
    return Outcome(status, "".join(out), "".join(err))


def test_the_run_returns_the_status_of_serve() -> None:
    assert fgraph(["mcp"], serve=lambda: 7).status == 7


def test_the_run_writes_no_output() -> None:
    assert fgraph(["mcp"], serve=lambda: 7).out == ""


def test_the_run_writes_no_error_output() -> None:
    assert fgraph(["mcp"], serve=lambda: 7).err == ""


def test_a_run_given_no_serve_serves_nothing() -> None:
    with pytest.raises(AssertionError, match="no serve"):
        fgraph(["mcp"])


def test_the_help_of_mcp_prints_its_usage_and_exits_with_zero() -> None:
    helped = fgraph(["mcp", "--help"])
    assert (helped.status, helped.out.startswith("usage: fgraph mcp")) == (0, True)
