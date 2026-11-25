"""The criterion of a term name that reads as an id: `fgraph add term f15` is refused at the add.

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
    ("name", "id_"),
    [("f15", "F-0015"), ("s3", "S-0003"), ("t7", "T-0007"), ("q4", "Q-0004")],
)
def test_a_term_name_that_reads_as_an_id_is_refused(name: str, id_: str, tmp_path: Path) -> None:
    status, _, err = fgraph(["add", "term", name, "--means", "a meaning"], tmp_path)
    assert (status, last_line(err)) == (
        2,
        f"fgraph: error: '{name}' reads as the id {id_}: a term name is no id",
    )


def test_a_term_name_that_reads_as_an_id_is_not_written(tmp_path: Path) -> None:
    fgraph(["add", "term", "f15", "--means", "a meaning"], tmp_path)
    assert not (tmp_path / ".fgraph" / "terms").exists()


def test_a_term_written_before_under_such_a_name_is_read_as_before(tmp_path: Path) -> None:
    terms = tmp_path / ".fgraph" / "terms"
    terms.mkdir(parents=True)
    (terms / "f15.toml").write_text(
        'name = "f15"\nmeaning = "a meaning"\nadded = 2026-01-01T00:00:00Z\n', "utf-8"
    )
    assert fgraph(["terms"], tmp_path) == (0, "f15  a meaning\n", "")


@pytest.mark.parametrize("name", ["f0", "x15", "f15a"])
def test_a_term_name_that_spells_no_id_is_added(name: str, tmp_path: Path) -> None:
    assert fgraph(["add", "term", name, "--means", "a meaning"], tmp_path) == (
        0,
        f"added {name}\n",
        "",
    )
