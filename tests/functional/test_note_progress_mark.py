"""The criterion of B-0033: a progress line given --standing or --open is refused, not marked.

Run end to end through `run` on a record in a temporary directory, through the file adapters of
the package; no git is opened. The red tests are strict xfails until the refusal is wired.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

XFAIL = pytest.mark.xfail(strict=True, reason="B-0033: a progress line drops the mark it is given")
NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
RECORD = (ADD_STORY, ADD_TASK, ["start", "S-0001"], ["start", "T-0001"])


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    try:
        status = run(
            argv,
            cwd,
            Path.is_dir,
            out.append,
            err.append,
            open_store=open_files,
            now=lambda: NOW,
            open_git=lambda _: None,
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


@pytest.fixture
def record(tmp_path: Path) -> Path:
    """A record whose started S-0001 holds the started T-0001."""
    for argv in RECORD:
        outcome = fgraph(argv, tmp_path)
        assert outcome.status == 0, outcome.err
    return tmp_path


@XFAIL
@pytest.mark.parametrize(
    ("item", "option"),
    [("S-0001", "--standing"), ("S-0001", "--open"), ("T-0001", "--standing")],
    ids=["item-standing", "item-open", "task-standing"],
)
def test_a_progress_line_given_a_mark_is_refused_naming_its_option(
    record: Path, item: str, option: str
) -> None:
    outcome = fgraph(["note", item, "--progress", "a text", option], record)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        [f"fgraph: error: a progress line takes no {option}: it is no knowledge line"],
    )


@XFAIL
def test_a_progress_line_given_a_mark_leaves_the_file_of_the_work_item_as_it_was(
    record: Path,
) -> None:
    path = record / ".fgraph" / "items" / "S-0001.toml"
    before = path.read_text()
    fgraph(["note", "S-0001", "--progress", "a text", "--standing"], record)
    assert path.read_text() == before


def test_a_finding_given_a_mark_is_kept_with_its_mark(record: Path) -> None:
    outcome = runs(record, ["note", "S-0001", "--finding", "x", "--standing"], ["show", "S-0001"])
    assert "  finding  2026-01-01  x  (standing)\n" in outcome.out
