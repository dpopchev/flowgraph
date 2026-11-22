"""fgraph graph given a format that is not json is refused naming it, and prints no document.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def graph(format_: str, cwd: Path) -> tuple[int, str, str]:
    """The exit status, the output and the error output of fgraph graph in that format in cwd."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    status = run(
        ["graph", "--format", format_],
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: NOW,
    )
    return status, "".join(out), "".join(err)


def test_graph_of_a_format_that_is_not_json_exits_with_two(tmp_path: Path) -> None:
    assert graph("xml", tmp_path)[0] == 2


def test_graph_of_a_format_that_is_not_json_names_the_format(tmp_path: Path) -> None:
    assert "--format 'xml' is not json" in graph("xml", tmp_path)[2]


def test_graph_of_a_format_that_is_not_json_prints_no_document(tmp_path: Path) -> None:
    assert graph("xml", tmp_path)[1] == ""
