"""The criterion of the terms a record refuses: a name, a meaning, a term it holds none of.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def fgraph(argv: list[str], cwd: Path) -> tuple[int, str, str]:
    """The exit status, the output and the error output of the command in cwd, on its record."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: NOW,
    )
    return status, "".join(out), "".join(err)


def last_line(text: str) -> str:
    """The last line of the error output."""
    return text.splitlines()[-1]


@pytest.mark.parametrize(
    ("argv", "said"),
    [
        (["add", "term", "Gate", "--means", "a"], "'Gate' is no term name: lowercase words"),
        (["add", "term", "S-0001", "--means", "a"], "'S-0001' reads as the id of an item"),
        (["add", "term", "gate", "--means", " "], "meaning is empty"),
        (["show", "gate"], "no term 'gate' in the record"),
    ],
    ids=["bad-name", "name-of-an-item", "blank-meaning", "show-of-no-term"],
)
def test_a_term_refused_exits_with_two_and_says_why(
    argv: list[str], said: str, tmp_path: Path
) -> None:
    status, _, err = fgraph(argv, tmp_path)
    assert (status, last_line(err).startswith(f"fgraph: error: {said}")) == (2, True)


def test_a_term_refused_is_not_written(tmp_path: Path) -> None:
    fgraph(["add", "term", "Gate", "--means", "a"], tmp_path)
    assert not (tmp_path / ".fgraph" / "terms").exists()


def test_terms_of_a_record_with_none_says_so_in_one_line(tmp_path: Path) -> None:
    assert fgraph(["terms"], tmp_path) == (0, "no terms in the record\n", "")
