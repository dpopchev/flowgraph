"""The criterion of S-0072: a line noted about a term is listed by the show of term and item.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(reason="S-0072: fgraph note takes no --about yet", strict=True),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
NOTE = ["note", "S-0001", "--decision", "a gate runs on main", "--about", "gate"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
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
    return Outcome(status, "".join(out), "".join(err))


@pytest.fixture
def noted(tmp_path: Path) -> Outcome:
    """The note of a decision about the term gate, on a record with that term and a Story."""
    fgraph(["add", "term", "gate", "--means", "a check before a landing"], tmp_path)
    fgraph(ADD_STORY, tmp_path)
    return fgraph(NOTE, tmp_path)


def test_note_about_a_term_exits_with_zero(noted: Outcome) -> None:
    assert noted.status == 0


def test_show_of_the_term_lists_the_line_with_the_id_of_the_story(
    noted: Outcome, tmp_path: Path
) -> None:
    shown = fgraph(["show", "gate"], tmp_path).out
    assert "    S-0001  decision  2026-01-01  a gate runs on main\n" in shown


def test_show_of_the_story_lists_the_term(noted: Outcome, tmp_path: Path) -> None:
    assert "(about gate)" in fgraph(["show", "S-0001"], tmp_path).out
