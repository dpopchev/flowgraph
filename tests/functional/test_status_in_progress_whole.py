"""The criterion of S-0132: `fgraph status` and `fgraph watch` list every started InProgress item.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it, so the order last started first is fixed.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
SIX_COMPLETED_TOP = "  ... 1 more\n"


def started(count: int) -> list[list[str]]:
    """The commands of a record with count started Stories, two of them under a started Feature."""
    argvs: list[list[str]] = [["add", "feature", "a feature title", "--criterion", "a criterion"]]
    for number in range(1, count + 1):
        story = ["add", "story", f"title {number}", *CRITERION]
        argvs.append([*story, "--parent", "F-0001"] if number <= 2 else story)
    for number in range(1, count + 1):
        argvs.append(
            ["add", "task", "a task title", "--parent", f"S-{number:04}", "--output", "an output"]
        )
    argvs.append(["start", "F-0001"])
    argvs.append(["start", "S-0002"])
    argvs.extend(["start", f"S-{number:04}"] for number in range(3, count + 1))
    argvs.extend(["start", f"T-{number:04}"] for number in range(1, count + 1))
    return argvs


SEVEN = started(7)
SIX = started(6)

SEVEN_FRAME = (
    "InProgress (6)\n"
    "  S-0007  0/1 T  title 7\n"
    "    => T-0007  a task title\n"
    "  S-0006  0/1 T  title 6\n"
    "    => T-0006  a task title\n"
    "  S-0005  0/1 T  title 5\n"
    "    => T-0005  a task title\n"
    "  S-0004  0/1 T  title 4\n"
    "    => T-0004  a task title\n"
    "  S-0003  0/1 T  title 3\n"
    "    => T-0003  a task title\n"
    "  F-0001  0/2 W  a feature title\n"
    "    S-0002  0/1 T  title 2\n"
    "      => T-0002  a task title\n"
    "    S-0001  0/1 T  title 1\n"
    "      => T-0001  a task title\n"
)

SIX_FRAME = (
    "InProgress (5)\n"
    "  S-0006  0/1 T  title 6\n"
    "    => T-0006  a task title\n"
    "  S-0005  0/1 T  title 5\n"
    "    => T-0005  a task title\n"
    "  S-0004  0/1 T  title 4\n"
    "    => T-0004  a task title\n"
    "  S-0003  0/1 T  title 3\n"
    "    => T-0003  a task title\n"
    "  F-0001  0/2 W  a feature title\n"
    "    S-0002  0/1 T  title 2\n"
    "      => T-0002  a task title\n"
    "    S-0001  0/1 T  title 1\n"
    "      => T-0001  a task title\n"
)


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, at: datetime) -> Outcome:
    """Run the command at that time in cwd, whose record is `.fgraph/`, on the files of it."""
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
        now=lambda: at,
    )
    return Outcome(status, "".join(out), "".join(err))


def after(cwd: Path, argvs: Sequence[Sequence[str]], last: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the one before, then the last; its outcome."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(last, cwd, START + timedelta(seconds=len(argvs)))


def in_progress(text: str) -> str:
    """The lines from the InProgress heading up to, not including, the Completed heading."""
    lines = text.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.startswith("InProgress ("))
    end = next(i for i, line in enumerate(lines) if line.startswith("Completed ("))
    return "".join(lines[start:end])


@pytest.fixture
def seven_status(tmp_path: Path) -> Outcome:
    return after(tmp_path, SEVEN, ["status"])


@pytest.fixture
def seven_watch(tmp_path: Path) -> Outcome:
    return after(tmp_path, SEVEN, ["watch", "--count", "1"])


def test_status_lists_all_seven_started_items_whole(seven_status: Outcome) -> None:
    assert in_progress(seven_status.out) == SEVEN_FRAME


def test_status_has_no_more_line_under_in_progress(seven_status: Outcome) -> None:
    assert not any(line.startswith("  ... ") for line in seven_status.out.splitlines())


def test_watch_lists_all_seven_started_items_whole(seven_watch: Outcome) -> None:
    assert in_progress(seven_watch.out) == SEVEN_FRAME


def test_the_criterion_as_written_lists_six_started_in_five_lines(tmp_path: Path) -> None:
    assert in_progress(after(tmp_path, SIX, ["status"]).out) == SIX_FRAME


def test_completed_keeps_its_top_five_with_one_more(tmp_path: Path) -> None:
    listed = after(tmp_path, SIX_COMPLETED, ["status"])
    assert listed.out.endswith(SIX_COMPLETED_TOP)


SIX_COMPLETED = [
    argv
    for number in range(1, 7)
    for argv in (
        ["add", "story", f"title {number}", *CRITERION],
        ["add", "task", "a task title", "--parent", f"S-{number:04}", "--output", "an output"],
        ["start", f"S-{number:04}"],
        ["start", f"T-{number:04}"],
        ["complete", f"T-{number:04}", "--commit", f"abc123{number}"],
        ["complete", f"S-{number:04}", "--commit", f"abc123{number}"],
    )
]
