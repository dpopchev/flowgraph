"""The criterion of S-0143: `fgraph note --progress` keeps a line on a work item and on its Task.

Run end to end through `run` on a record in a temporary directory, through the file adapters of
the package; no git is opened.
"""

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
RECORD = (ADD_STORY, ADD_TASK, ["start", "S-0001"], ["start", "T-0001"])
HAND_OFF = "the parser is read; next the show"
RED_LINE = "red: 1 failed"
NOTE_ITEM = ["note", "S-0001", "--progress", HAND_OFF]
NOTE_TASK = ["note", "T-0001", "--progress", RED_LINE]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer sees it"]
NOT_KNOWLEDGE = "a progress line takes no --about and no --governs: it is no knowledge line"
NO_FEATURE = (
    "F-0001 keeps no progress line: fgraph note --progress takes a work item or a Task of it"
)
XFAIL = pytest.mark.xfail(strict=True, reason="S-0143: fgraph note takes no progress line")


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


def held(cwd: Path) -> dict[str, object]:
    """The file of S-0001 as tomllib reads it."""
    return tomllib.loads((cwd / ".fgraph" / "items" / "S-0001.toml").read_text())


@XFAIL
def test_a_progress_line_noted_on_a_work_item_says_noted(record: Path) -> None:
    outcome = fgraph(NOTE_ITEM, record)
    assert (outcome.status, outcome.out) == (0, "noted S-0001\n")


@XFAIL
def test_a_progress_line_noted_on_a_task_says_noted_of_its_work_item(record: Path) -> None:
    outcome = fgraph(NOTE_TASK, record)
    assert (outcome.status, outcome.out) == (0, "noted T-0001 of S-0001\n")


@XFAIL
def test_the_file_of_the_work_item_keeps_both_lines_with_their_time(record: Path) -> None:
    runs(record, NOTE_ITEM, NOTE_TASK)
    assert held(record).get("progress") == [
        {"text": HAND_OFF, "noted": NOW},
        {"text": RED_LINE, "noted": NOW, "task": "T-0001"},
    ]


@XFAIL
def test_show_lists_the_line_of_the_task_under_it_and_that_of_the_item_last(
    record: Path,
) -> None:
    outcome = runs(record, NOTE_ITEM, NOTE_TASK, ["show", "S-0001"])
    assert outcome.out.endswith(
        "Tasks (1)\n"
        "  T-0001  a task title\n"
        "    bucket           InProgress\n"
        "    expected output  an output\n"
        "    progress         2026-01-01  red: 1 failed\n"
        "Progress (1)\n"
        "  2026-01-01  the parser is read; next the show\n"
    )


@XFAIL
def test_show_lists_the_lines_of_the_item_in_the_order_noted(record: Path) -> None:
    first = ["note", "S-0001", "--progress", "the first"]
    second = ["note", "S-0001", "--progress", "the second"]
    outcome = runs(record, first, second, ["show", "S-0001"])
    assert outcome.out.endswith("Progress (2)\n  2026-01-01  the first\n  2026-01-01  the second\n")


@XFAIL
def test_knowledge_lists_no_progress_line(record: Path) -> None:
    noted = runs(record, NOTE_ITEM, NOTE_TASK)
    knowledge = fgraph(["knowledge"], record)
    assert (noted.status, knowledge.out) == (0, "no knowledge lines in the record\n")


@XFAIL
@pytest.mark.parametrize(
    "script",
    [
        (ADD_STORY,),
        (
            *RECORD,
            ["complete", "T-0001", "--commit", "abc1234"],
            ["complete", "S-0001", "--commit", "abc1234"],
        ),
        (ADD_STORY, ["remove", "S-0001", "--reason", "a reason"]),
    ],
    ids=["in-backlog", "completed", "removed"],
)
def test_a_work_item_in_any_state_takes_a_progress_line(
    tmp_path: Path, script: Sequence[Sequence[str]]
) -> None:
    outcome = runs(tmp_path, *script, NOTE_ITEM)
    assert (outcome.status, outcome.out) == (0, "noted S-0001\n")


@XFAIL
def test_a_task_in_backlog_takes_a_progress_line(tmp_path: Path) -> None:
    outcome = runs(tmp_path, ADD_STORY, ADD_TASK, NOTE_TASK)
    assert (outcome.status, outcome.out) == (0, "noted T-0001 of S-0001\n")


@XFAIL
@pytest.mark.parametrize(
    ("script", "line"),
    [
        ((["note", "S-0001", "--progress", " "],), "text is empty"),
        ((["note", "T-0009", "--progress", "x"],), "no Task T-0009 in the record"),
        ((["note", "S-0009", "--progress", "x"],), "no Story S-0009 in the record"),
        ((ADD_FEATURE, ["note", "F-0001", "--progress", "x"]), NO_FEATURE),
        (([*NOTE_ITEM, "--about", "gate"],), NOT_KNOWLEDGE),
        (([*NOTE_ITEM, "--governs", "src/a.py"],), NOT_KNOWLEDGE),
    ],
    ids=["a-blank-text", "a-wrong-task", "a-wrong-item", "a-feature", "about", "governs"],
)
def test_a_refused_progress_line_names_why(
    record: Path, script: Sequence[Sequence[str]], line: str
) -> None:
    outcome = runs(record, *script)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [f"fgraph: error: {line}"])


@XFAIL
def test_a_blank_progress_line_writes_nothing(record: Path) -> None:
    before = (record / ".fgraph" / "items" / "S-0001.toml").read_text()
    outcome = fgraph(["note", "S-0001", "--progress", " "], record)
    after = (record / ".fgraph" / "items" / "S-0001.toml").read_text()
    assert (outcome.status, outcome.err.splitlines()[-1:], after == before) == (
        2,
        ["fgraph: error: text is empty"],
        True,
    )


@XFAIL
def test_a_progress_line_and_a_finding_in_one_note_are_refused(
    record: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fgraph(["note", "S-0001", "--progress", "a", "--finding", "b"], record)
    assert "not allowed with argument" in capsys.readouterr().err


def test_a_finding_on_a_task_stays_refused(record: Path) -> None:
    outcome = fgraph(["note", "T-0001", "--finding", "x"], record)
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (
        2,
        ["fgraph: error: 'T-0001' is no Story, Upkeep, Bug or Spike id"],
    )


def test_a_finding_on_the_work_item_is_still_listed_under_knowledge(record: Path) -> None:
    outcome = runs(record, ["note", "S-0001", "--finding", "x"], ["show", "S-0001"])
    assert outcome.out.endswith("Knowledge (1)\n  finding  2026-01-01  x\n")
