"""A term that is not in the record is refused where an item or a line names it: nothing is written.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
SAID = "fgraph: error: no term 'nope' in the record: add it with fgraph add term"
ABOUT = ["--about", "nope"]


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


def held(record: Path) -> dict[str, str]:
    """The text of every file of the record, by its path inside it."""
    return {
        str(path.relative_to(record)): path.read_text(encoding="utf-8")
        for path in sorted(record.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def items(tmp_path: Path) -> Path:
    """A record with the term gate, the Story S-0001 and the Feature F-0001."""
    fgraph(["add", "term", "gate", "--means", "a check before a landing"], tmp_path)
    fgraph(["add", "story", "a title", *CRITERION], tmp_path)
    fgraph(["add", "feature", "a feature title", "--criterion", "a developer sees it"], tmp_path)
    return tmp_path


COMMANDS = [
    ["add", "story", "another", *CRITERION, *ABOUT],
    ["add", "bug", "another", "--observed", "a", "--expected", "b", *ABOUT],
    ["add", "feature", "another", "--criterion", "a developer sees it", *ABOUT],
    ["amend", "S-0001", *ABOUT],
    ["amend", "F-0001", *ABOUT],
    ["note", "S-0001", "--finding", "a text", *ABOUT],
    ["note", "F-0001", "--finding", "a text", *ABOUT],
    ["note", "S-0001", "--finding", "a text", "--about", "gate", *ABOUT],
]
IDS = [
    "add-story",
    "add-bug",
    "add-feature",
    "amend-story",
    "amend-feature",
    "note-story",
    "note-feature",
    "note-after-a-term-of-the-record",
]


@pytest.mark.parametrize("argv", COMMANDS, ids=IDS)
def test_a_term_not_in_the_record_is_refused_with_two_naming_how_to_add_it(
    argv: list[str], items: Path
) -> None:
    refused = fgraph(argv, items)
    assert (refused.status, refused.err.splitlines()[-1]) == (2, SAID)


@pytest.mark.parametrize("argv", COMMANDS, ids=IDS)
def test_a_term_not_in_the_record_leaves_the_record_as_it_was(argv: list[str], items: Path) -> None:
    before = held(items / ".fgraph")
    fgraph(argv, items)
    assert held(items / ".fgraph") == before


def test_none_given_with_a_term_is_refused(items: Path) -> None:
    refused = fgraph(["amend", "S-0001", "--about", "none", "--about", "gate"], items)
    assert (refused.status, refused.err.splitlines()[-1]) == (
        2,
        "fgraph: error: none stands alone: it takes every term away",
    )
