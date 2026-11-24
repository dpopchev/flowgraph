"""The criterion of S-0102: a finding noted as open is listed with its mark by show and knowledge.

Run end to end on the files of a record in a temporary directory, through run() of the package.
"""

import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

ADD_STORY = ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer lists the record"]
ADD_TERM = ["add", "term", "gate", "--means", "a check a landing runs"]
OPEN_NOTE = ["note", "S-0001", "--finding", "the queue is one file", "--open"]
XFAIL = pytest.mark.xfail(strict=True, reason="S-0102: fgraph note takes no mark")


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path, day: int = 1) -> Outcome:
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
            open_git=lambda _: None,
            now=lambda: datetime(2026, 1, day, tzinfo=UTC),
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


@pytest.fixture
def story(tmp_path: Path) -> Path:
    fgraph(ADD_STORY, tmp_path)
    return tmp_path


@XFAIL
def test_note_of_an_open_finding_exits_with_zero_and_says_noted(story: Path) -> None:
    outcome = fgraph(OPEN_NOTE, story)
    assert (outcome.status, outcome.out) == (0, "noted S-0001\n")


@XFAIL
def test_show_of_a_work_item_lists_an_open_finding_with_its_mark(story: Path) -> None:
    fgraph(OPEN_NOTE, story)
    assert fgraph(["show", "S-0001"], story).out.endswith(
        "Tasks (0)\nKnowledge (1)\n  finding  2026-01-01  the queue is one file  (open)\n"
    )


@XFAIL
def test_knowledge_lists_an_open_finding_with_its_mark(story: Path) -> None:
    fgraph(OPEN_NOTE, story)
    assert fgraph(["knowledge"], story).out == (
        "2026-01-01  finding  S-0001  the queue is one file  (open)\n"
    )


@XFAIL
def test_show_of_a_work_item_lists_a_standing_decision_with_its_mark(story: Path) -> None:
    fgraph(["note", "S-0001", "--decision", "keep one store", "--standing"], story)
    assert fgraph(["show", "S-0001"], story).out.endswith(
        "  decision  2026-01-01  keep one store  (standing)\n"
    )


@XFAIL
def test_knowledge_of_a_kind_lists_an_open_deviation_with_its_mark(story: Path) -> None:
    fgraph(["note", "S-0001", "--deviation", "a task was dropped", "--open"], story)
    assert fgraph(["knowledge", "--kind", "deviation"], story).out.endswith("  (open)\n")


@XFAIL
def test_show_of_a_feature_lists_a_standing_decision_with_its_mark(tmp_path: Path) -> None:
    fgraph(ADD_FEATURE, tmp_path)
    fgraph(["note", "F-0001", "--decision", "the budget is agreed", "--standing"], tmp_path)
    assert fgraph(["show", "F-0001"], tmp_path).out.endswith(
        "Knowledge (1)\n  decision  2026-01-01  the budget is agreed  (standing)\n"
    )


@XFAIL
def test_knowledge_lists_the_mark_before_the_term_the_line_is_about(story: Path) -> None:
    fgraph(ADD_TERM, story)
    fgraph([*OPEN_NOTE, "--about", "gate"], story)
    assert fgraph(["knowledge"], story).out == (
        "2026-01-01  finding  S-0001  the queue is one file  (open)  (about gate)\n"
    )


@XFAIL
def test_the_file_of_the_work_item_holds_the_mark_of_the_line(story: Path) -> None:
    fgraph(OPEN_NOTE, story)
    held = tomllib.loads((story / ".fgraph" / "items" / "S-0001.toml").read_text())
    assert held["knowledge"][0]["mark"] == "open"


def test_show_of_a_work_item_lists_a_line_with_no_mark_as_before(story: Path) -> None:
    fgraph(["note", "S-0001", "--finding", "the file holds it"], story)
    assert fgraph(["show", "S-0001"], story).out.endswith(
        "  finding  2026-01-01  the file holds it\n"
    )


def test_the_file_of_a_line_with_no_mark_holds_no_other_key_than_before(story: Path) -> None:
    fgraph(["note", "S-0001", "--finding", "the file holds it"], story)
    held = tomllib.loads((story / ".fgraph" / "items" / "S-0001.toml").read_text())
    assert set(held["knowledge"][0]) == {"kind", "text", "noted"}


def test_note_of_both_marks_is_refused_and_writes_nothing(story: Path) -> None:
    outcome = fgraph(["note", "S-0001", "--finding", "a text", "--standing", "--open"], story)
    shown = fgraph(["show", "S-0001"], story).out.splitlines()[-1]
    assert (outcome.status, shown) == (2, "Tasks (0)")
