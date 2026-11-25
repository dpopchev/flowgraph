"""The criterion of S-0081: `fgraph knowledge` ends each line noted with --governs with its files.

The line ends as `fgraph show` ends it. Run end to end through `run` on the file adapters of a
temporary record, with no git, so a --governs path is kept as given.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

# Each command with the day of January 2026 it is run on: the lines are noted on different days.
SCRIPT = [
    (1, ["add", "term", "gate", "--means", "a check before a landing"]),
    (1, ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]),
    (2, ["note", "S-0001", "--finding", "the store is plain files", "--about", "gate"]),
    (
        3,
        [
            "note",
            "S-0001",
            "--decision",
            "keep one store",
            "--governs",
            "src/store.py",
            "--governs",
            "src/files.py",
        ],
    ),
    (
        4,
        [
            "note",
            "S-0001",
            "--finding",
            "is the queue one file too",
            "--open",
            "--about",
            "gate",
            "--governs",
            "src/queue.py",
        ],
    ),
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path, day: int) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record, no git."""
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
        now=lambda: datetime(2026, 1, day, tzinfo=UTC),
    )
    return Outcome(status, "".join(out), "".join(err))


def listed(recorded: Path, *options: str) -> Outcome:
    """The outcome of fgraph knowledge with the options, run on day 5 of the record."""
    return fgraph(["knowledge", *options], recorded, 5)


def tail(out: str, text: str) -> str:
    """What follows text on the first line of out that holds it."""
    return next(line for line in out.splitlines() if text in line).split(text, 1)[1]


@pytest.fixture
def recorded(tmp_path: Path) -> Path:
    for day, argv in SCRIPT:
        assert fgraph(argv, tmp_path, day).status == 0, " ".join(argv)
    return tmp_path


def test_knowledge_lists_the_files_a_line_governs_at_its_end(recorded: Path) -> None:
    assert listed(recorded).out == (
        "2026-01-04  finding  S-0001#3  is the queue one file too  (open)  (about gate)"
        "  (governs src/queue.py)\n"
        "2026-01-03  decision  S-0001#2  keep one store  (governs src/store.py, src/files.py)\n"
        "2026-01-02  finding  S-0001#1  the store is plain files  (about gate)\n"
    )


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("keep one store", id="decision"),
        pytest.param("is the queue one file too", id="finding"),
    ],
)
def test_knowledge_ends_a_line_as_show_ends_it(text: str, recorded: Path) -> None:
    assert tail(listed(recorded).out, text) == tail(
        fgraph(["show", "S-0001"], recorded, 5).out, text
    )


def test_knowledge_of_a_kind_lists_the_files_of_its_decision(recorded: Path) -> None:
    assert listed(recorded, "--kind", "decision").out == (
        "2026-01-03  decision  S-0001#2  keep one store  (governs src/store.py, src/files.py)\n"
    )


def test_knowledge_about_a_term_lists_the_files_of_its_finding(recorded: Path) -> None:
    assert listed(recorded, "--about", "gate").out.splitlines()[0] == (
        "2026-01-04  finding  S-0001#3  is the queue one file too  (open)  (about gate)"
        "  (governs src/queue.py)"
    )


def test_knowledge_with_a_line_that_governs_files_exits_with_zero(recorded: Path) -> None:
    assert listed(recorded).status == 0


def test_knowledge_lists_a_line_that_governs_no_file_as_before(recorded: Path) -> None:
    assert (
        "2026-01-02  finding  S-0001#1  the store is plain files  (about gate)"
        in listed(recorded).out.splitlines()
    )


def test_knowledge_as_json_holds_the_files_a_line_governs(recorded: Path) -> None:
    document = json.loads(listed(recorded, "--format", "json").out)
    assert [line["governs"] for line in document["lines"] if line["ref"] == "S-0001#2"] == [
        ["src/store.py", "src/files.py"]
    ]
