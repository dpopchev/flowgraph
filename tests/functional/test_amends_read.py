"""The read of a record refuses an amends of a work item that is not completed, as the write does.

A Bug file edited by hand to amend a work item in Backlog, started, blocked or removed is refused by
the read of each command: exit 2 with one line naming the file, and a write then changes no file.
The red tests are marked xfail until the read refuses it. Run end to end on a record in a temporary
directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from tests.functional.completed_story import ADD_STORY, CRITERION, STANDING_ALONE

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_BUG = [
    "add",
    "bug",
    "a bug title",
    "--observed",
    "it fails",
    "--expected",
    "it works",
    "--amends",
    "S-0001",
]
LINE = "fgraph: error: {path}: amends names {named}, which is not completed"
XFAIL = pytest.mark.xfail(strict=True, reason="B-0028: the read takes an amends the write refuses")


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


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def refused(outcome: Outcome) -> tuple[int, list[str]]:
    """The exit status of a run and the last line it wrote on the error output, if any."""
    return outcome.status, outcome.err.splitlines()[-1:]


def task_of(item: str) -> list[str]:
    """The add of a Task of the work item named."""
    return ["add", "task", "a task title", "--parent", item, "--output", "an output"]


def files_of(record: Path) -> dict[Path, str]:
    """The text of every file of the record, by its path."""
    return {path: path.read_text(encoding="utf-8") for path in record.rglob("*") if path.is_file()}


def amending(cwd: Path, named: str) -> Path:
    """Edit the Bug to amend the work item named by hand, and give the path of its file."""
    path = cwd / ".fgraph" / "items" / "B-0001.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('amends = "S-0001"', f'amends = "{named}"', 1), encoding="utf-8")
    return path


@pytest.fixture
def record(tmp_path: Path) -> Path:
    """The record of a completed Story, a Story in Backlog, a removed one, a started one, a blocked
    one and a Bug amending the completed one, as fgraph wrote it."""
    steps = [
        *STANDING_ALONE,
        ADD_STORY,
        ADD_STORY,
        ADD_STORY,
        ADD_STORY,
        ["remove", "S-0003", "--reason", "a reason"],
        task_of("S-0004"),
        ["start", "S-0004"],
        task_of("S-0005"),
        ["start", "S-0005"],
        ["block", "S-0005", "--reason", "a reason", "--waiting-on", "a party"],
        ADD_BUG,
    ]
    for argv in steps:
        assert fgraph(argv, tmp_path).status == 0
    return tmp_path


@XFAIL
@pytest.mark.parametrize(
    "named",
    ["S-0002", "S-0003", "S-0004", "S-0005"],
    ids=["backlog", "removed", "started", "blocked"],
)
def test_status_of_a_bug_amending_a_work_item_not_completed_exits_with_two_naming_the_file(
    named: str, record: Path
) -> None:
    path = amending(record, named)
    outcome = runs(record, ["status"])
    assert refused(outcome) == (2, [LINE.format(path=path, named=named)])


@XFAIL
@pytest.mark.parametrize(
    "argv",
    [["show", "B-0001"], ["show", "S-0002"]],
    ids=["the-bug", "the-amended"],
)
def test_show_of_a_bug_amending_a_work_item_not_completed_exits_with_two_naming_the_file(
    argv: list[str], record: Path
) -> None:
    path = amending(record, "S-0002")
    outcome = runs(record, argv)
    assert refused(outcome) == (2, [LINE.format(path=path, named="S-0002")])


@XFAIL
def test_a_write_of_a_record_amending_a_work_item_not_completed_leaves_every_file_as_it_was(
    record: Path,
) -> None:
    amending(record, "S-0002")
    held = files_of(record / ".fgraph")
    runs(record, ["add", "story", "another title", *CRITERION])
    assert files_of(record / ".fgraph") == held


def test_status_of_a_record_whose_bug_amends_a_completed_work_item_exits_with_zero(
    record: Path,
) -> None:
    assert runs(record, ["status"]).status == 0
