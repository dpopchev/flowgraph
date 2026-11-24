"""The criterion of S-0146: `fgraph knowledge --search TEXT` lists the lines whose text holds it.

Run end to end through `run` on a record in a temporary directory, through the file adapters of
the package. The red tests are strict xfails naming S-0146 until the search is taken; the guards
pass today and after.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

XFAIL = pytest.mark.xfail(strict=True, reason="S-0146: fgraph knowledge takes no --search")

# What a Spike is completed with: its decision and its answer.
DECIDED = ["--decision", "one file per item", "--answer", "yes"]

# Each command with the day of January 2026 it is run on: the lines are noted on different days.
SCRIPT = [
    (1, ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]),
    (1, ["add", "spike", "a spike title", "--hypothesis", "Can one file hold it?"]),
    (1, ["add", "task", "a task title", "--parent", "Q-0001", "--output", "an output"]),
    (1, ["add", "term", "gate", "--means", "a check before a landing"]),
    (2, ["note", "S-0001", "--finding", "the Store is plain files"]),
    (3, ["note", "S-0001", "--decision", "keep one store", "--about", "gate"]),
    (4, ["add", "feature", "a feature title", "--criterion", "a developer lists the record"]),
    (4, ["note", "F-0001", "--decision", "ship in two steps"]),
    (5, ["start", "Q-0001"]),
    (5, ["start", "T-0001"]),
    (5, ["complete", "T-0001", "--commit", "abc1234"]),
    (5, ["complete", "Q-0001", "--commit", "def5678", *DECIDED]),
    (6, ["note", "S-0001", "--deviation", "a task was dropped"]),
]

STORE = "2026-01-03  decision  S-0001  keep one store  (about gate)\n"
PLAIN = "2026-01-02  finding  S-0001  the Store is plain files\n"


def none(what: str) -> str:
    """The one line fgraph knowledge writes when no line of the record meets the search."""
    return f"no {what} in the record\n"


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, day: int) -> Outcome:
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


def record(tmp_path: Path) -> Path:
    """Run every command of the script in tmp_path, each one exiting with zero."""
    for day, argv in SCRIPT:
        assert fgraph(argv, tmp_path, day).status == 0, argv
    return tmp_path


@pytest.fixture
def recorded(tmp_path: Path) -> Path:
    return record(tmp_path)


def search(cwd: Path, *options: str) -> Outcome:
    """Run fgraph knowledge with the options, on day 7 of January 2026."""
    return fgraph(["knowledge", *options], cwd, 7)


@XFAIL
def test_search_lists_the_lines_whose_text_holds_the_text_newest_first(recorded: Path) -> None:
    result = search(recorded, "--search", "STORE")
    assert (result.status, result.out) == (0, STORE + PLAIN)


@XFAIL
def test_search_narrowed_to_a_kind_lists_the_lines_meeting_both(recorded: Path) -> None:
    result = search(recorded, "--search", "store", "--kind", "decision")
    assert (result.status, result.out) == (0, STORE)


@XFAIL
def test_search_narrowed_to_a_term_lists_the_lines_meeting_both(recorded: Path) -> None:
    result = search(recorded, "--search", "store", "--about", "gate")
    assert (result.status, result.out) == (0, STORE)


@XFAIL
def test_search_and_a_term_holding_no_such_line_says_so(recorded: Path) -> None:
    result = search(recorded, "--search", "plain", "--about", "gate")
    assert (result.status, result.out) == (
        0,
        none("knowledge lines about gate holding 'plain'"),
    )


@XFAIL
def test_search_finds_a_part_of_a_word(recorded: Path) -> None:
    result = search(recorded, "--search", "tw")
    assert (result.status, result.out) == (
        0,
        "2026-01-04  decision  F-0001  ship in two steps\n",
    )


@XFAIL
def test_search_finds_the_decision_of_a_spike_with_its_answer(recorded: Path) -> None:
    result = search(recorded, "--search", "ANSWER YES")
    assert (result.status, result.out) == (
        0,
        "2026-01-05  decision  Q-0001  one file per item (answer yes)\n",
    )


@XFAIL
@pytest.mark.parametrize("text", ["a title", "S-0001", "gate", "finding"])
def test_search_does_not_search_the_title_the_id_the_term_or_the_kind(
    text: str, recorded: Path
) -> None:
    result = search(recorded, "--search", text)
    assert (result.status, result.out) == (0, none(f"knowledge lines holding {text!r}"))


@XFAIL
def test_search_of_a_kind_holding_no_such_line_says_so(recorded: Path) -> None:
    result = search(recorded, "--search", "zzz", "--kind", "finding")
    assert (result.status, result.out) == (0, none("finding lines holding 'zzz'"))


@XFAIL
def test_a_blank_search_is_refused_with_exit_two(recorded: Path) -> None:
    result = search(recorded, "--search", " ")
    assert (result.status, result.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: search is empty"],
    )


def test_knowledge_without_a_search_lists_every_line_newest_first(recorded: Path) -> None:
    assert search(recorded).out == (
        "2026-01-06  deviation  S-0001  a task was dropped\n"
        "2026-01-05  decision  Q-0001  one file per item (answer yes)\n"
        "2026-01-04  decision  F-0001  ship in two steps\n"
        "2026-01-03  decision  S-0001  keep one store  (about gate)\n"
        "2026-01-02  finding  S-0001  the Store is plain files\n"
    )


def test_knowledge_of_a_kind_without_a_search_lists_that_kind_alone(recorded: Path) -> None:
    assert search(recorded, "--kind", "finding").out == PLAIN
