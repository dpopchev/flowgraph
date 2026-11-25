"""The criterion of S-0155: `fgraph knowledge --format json` prints the lines the text lists.

The lines are printed as one JSON document.

Run end to end through `run` on the file adapters of a temporary record, with no git.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

XFAIL = pytest.mark.xfail(strict=True, reason="S-0155: fgraph knowledge takes no --format")
XML_REFUSAL = "--format 'xml' is not text or json, the two formats of knowledge"

# Each command with the day of January 2026 it is run on: the lines are noted on different days.
SCRIPT = [
    (1, ["add", "term", "gate", "--means", "a check before a landing"]),
    (1, ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]),
    (2, ["note", "S-0001", "--finding", "the store is plain files", "--about", "gate"]),
    (3, ["note", "S-0001", "--decision", "keep one store", "--governs", "src/store.py"]),
    (4, ["note", "S-0001", "--deviation", "a task was dropped"]),
    (5, ["note", "S-0001", "--decision", "keep one file per item", "--supersedes", "S-0001#2"]),
]

ALL_REFS = ["S-0001#4", "S-0001#3", "S-0001#2", "S-0001#1"]


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


def listed(recorded: Path, *options: str) -> Outcome:
    """The outcome of fgraph knowledge with the options, run on day 6 of the record."""
    return fgraph(["knowledge", *options], recorded, 6)


def document(recorded: Path, *options: str) -> dict[str, list[dict[str, object]]]:
    """The JSON document fgraph knowledge prints for the options, parsed."""
    return json.loads(listed(recorded, *options, "--format", "json").out)


def refs_of_text(out: str) -> list[str]:
    """The ref column of the lines of the text listing."""
    return [line.split("  ")[2] for line in out.splitlines()]


@pytest.fixture
def recorded(tmp_path: Path) -> Path:
    for day, argv in SCRIPT:
        assert fgraph(argv, tmp_path, day).status == 0, " ".join(argv)
    return tmp_path


@XFAIL
def test_knowledge_as_json_lists_the_lines_newest_first_by_ref(recorded: Path) -> None:
    assert [line["ref"] for line in document(recorded)["lines"]] == ALL_REFS


@XFAIL
def test_knowledge_as_json_line_of_the_decision_is_whole(recorded: Path) -> None:
    assert document(recorded)["lines"][2] == {
        "about": [],
        "governs": ["src/store.py"],
        "item": "S-0001",
        "kind": "decision",
        "mark": None,
        "noted": "2026-01-03T00:00:00+00:00",
        "ref": "S-0001#2",
        "supersedes": [],
        "text": "keep one store",
    }


@XFAIL
def test_knowledge_as_json_line_of_the_finding_holds_its_about(recorded: Path) -> None:
    assert document(recorded)["lines"][3]["about"] == ["gate"]


@XFAIL
def test_knowledge_as_json_line_of_the_superseding_decision_holds_what_it_supersedes(
    recorded: Path,
) -> None:
    assert document(recorded)["lines"][0]["supersedes"] == ["S-0001#2"]


@pytest.mark.parametrize(
    ("options", "refs"),
    [
        pytest.param((), ALL_REFS, id="all", marks=XFAIL),
        pytest.param(("--kind", "decision"), ["S-0001#4", "S-0001#2"], id="kind", marks=XFAIL),
        pytest.param(("--about", "gate"), ["S-0001#1"], id="about", marks=XFAIL),
        pytest.param(("--search", "STORE"), ["S-0001#2", "S-0001#1"], id="search", marks=XFAIL),
        pytest.param(("--live",), ["S-0001#4", "S-0001#3", "S-0001#1"], id="live", marks=XFAIL),
    ],
)
def test_knowledge_as_json_holds_the_refs_listed_for_the_options(
    options: tuple[str, ...], refs: list[str], recorded: Path
) -> None:
    assert [line["ref"] for line in document(recorded, *options)["lines"]] == refs


@pytest.mark.parametrize(
    "options",
    [
        pytest.param((), id="all", marks=XFAIL),
        pytest.param(("--kind", "decision"), id="kind", marks=XFAIL),
        pytest.param(("--about", "gate"), id="about", marks=XFAIL),
        pytest.param(("--search", "STORE"), id="search", marks=XFAIL),
        pytest.param(("--live",), id="live", marks=XFAIL),
    ],
)
def test_knowledge_as_json_holds_the_same_refs_as_the_text_for_the_options(
    options: tuple[str, ...], recorded: Path
) -> None:
    assert [line["ref"] for line in document(recorded, *options)["lines"]] == refs_of_text(
        listed(recorded, *options).out
    )


@XFAIL
def test_knowledge_as_json_of_a_filter_with_no_line_is_an_empty_document(recorded: Path) -> None:
    assert document(recorded, "--kind", "deviation", "--about", "gate") == {"lines": []}


@XFAIL
def test_knowledge_as_json_is_canonical_json_with_a_newline(recorded: Path) -> None:
    out = listed(recorded, "--format", "json").out
    assert out == json.dumps(json.loads(out), indent=2, sort_keys=True) + "\n"


@XFAIL
def test_knowledge_as_json_is_the_same_bytes_on_a_second_run(recorded: Path) -> None:
    first = listed(recorded, "--format", "json").out
    second = listed(recorded, "--format", "json").out
    assert second == json.dumps(json.loads(first), indent=2, sort_keys=True) + "\n"


@XFAIL
def test_knowledge_format_text_prints_what_no_format_prints(recorded: Path) -> None:
    assert listed(recorded, "--format", "text").out == listed(recorded).out


@XFAIL
def test_knowledge_format_xml_is_refused_naming_both_formats(recorded: Path) -> None:
    assert XML_REFUSAL in listed(recorded, "--format", "xml").err


def test_knowledge_format_xml_exits_with_two(recorded: Path) -> None:
    assert listed(recorded, "--format", "xml").status == 2


def test_knowledge_format_xml_prints_nothing_on_stdout(recorded: Path) -> None:
    assert listed(recorded, "--format", "xml").out == ""


def test_knowledge_text_lists_the_refs_newest_first(recorded: Path) -> None:
    assert refs_of_text(listed(recorded).out) == ALL_REFS
