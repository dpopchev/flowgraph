"""The criterion of S-0130: status and watch list the first line of the Backlog with no flag.

`fgraph status` and `fgraph watch --count 1` list the first line of the Backlog alone, then how
many more there are and how many of them can start; `--backlog` lists the whole of it.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
SIX = range(1, 7)


def story(number: int) -> list[str]:
    """The command that adds the Story of that title."""
    return ["add", "story", f"title {number}", *CRITERION]


def completed(number: int) -> list[list[str]]:
    """The commands that add the Story of that number with one Task and complete both."""
    story_id, task, commit = f"S-{number:04}", f"T-{number:04}", f"abc123{number}"
    return [
        story(number),
        ["add", "task", "a task title", "--parent", story_id, "--output", "an output"],
        ["start", story_id],
        ["start", task],
        ["complete", task, "--commit", commit],
        ["complete", story_id, "--commit", commit],
    ]


SIX_COMPLETED = [argv for number in SIX for argv in completed(number)]
FIVE = [story(number) for number in range(1, 6)]
WAITING = [*FIVE, ["amend", "S-0001", "--depends-on", "S-0002"]]
BESIDE = [*SIX_COMPLETED, *(story(number) for number in range(7, 12))]
ONE = [story(1)]

WHOLE = (
    "Backlog (5)\n"
    "> S-0001  title 1\n"
    "  S-0002  title 2\n"
    "  S-0003  title 3\n"
    "  S-0004  title 4\n"
    "  S-0005  title 5\n"
    "InProgress (0)\n"
    "Completed (0)\n"
)
SHORT = "Backlog (5)\n> S-0001  title 1\n  ... 4 more, 0 can start\nInProgress (0)\nCompleted (0)\n"


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
        wait=lambda _: None,
    )
    return Outcome(status, "".join(out), "".join(err))


def after(cwd: Path, argvs: Sequence[Sequence[str]], last: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the one before, then the last; its outcome."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(last, cwd, START + timedelta(seconds=len(argvs)))


def pair(listed: Outcome) -> tuple[int, str]:
    """The exit status and the output of a run, the two facts of one behavior."""
    return listed.status, listed.out


def test_status_lists_the_first_line_of_the_backlog_alone(tmp_path: Path) -> None:
    assert pair(after(tmp_path, FIVE, ["status"])) == (0, SHORT)


def test_watch_lists_the_first_line_of_the_backlog_alone(tmp_path: Path) -> None:
    assert pair(after(tmp_path, FIVE, ["watch", "--count", "1"])) == (0, SHORT)


def test_status_counts_the_next_to_start_the_top_leaves_out_and_does_not_list_it(
    tmp_path: Path,
) -> None:
    listed = after(tmp_path, WAITING, ["status"])
    assert listed.out.splitlines()[1:3] == [
        "~ S-0001  title 1  -- depends on S-0002",
        "  ... 4 more, 1 can start",
    ]


def test_status_backlog_lists_the_whole_backlog(tmp_path: Path) -> None:
    assert pair(after(tmp_path, FIVE, ["status", "--backlog"])) == (0, WHOLE)


def test_watch_backlog_lists_the_whole_backlog(tmp_path: Path) -> None:
    assert pair(after(tmp_path, FIVE, ["watch", "--backlog", "--count", "1"])) == (0, WHOLE)


def test_status_backlog_leaves_completed_at_its_top_five(tmp_path: Path) -> None:
    listed = after(tmp_path, BESIDE, ["status", "--backlog"])
    lines = listed.out.splitlines()
    assert lines[lines.index("Completed (6)") :] == [
        "Completed (6)",
        "  S-0006  abc1236  title 6",
        "  S-0005  abc1235  title 5",
        "  S-0004  abc1234  title 4",
        "  S-0003  abc1233  title 3",
        "  S-0002  abc1232  title 2",
        "  ... 1 more",
    ]


def test_status_all_lists_the_whole_backlog(tmp_path: Path) -> None:
    assert pair(after(tmp_path, FIVE, ["status", "--all"])) == (0, WHOLE)


def test_watch_all_lists_the_whole_backlog(tmp_path: Path) -> None:
    assert pair(after(tmp_path, FIVE, ["watch", "--all", "--count", "1"])) == (0, WHOLE)


def test_status_json_lists_every_item_of_the_backlog(tmp_path: Path) -> None:
    listed = after(tmp_path, FIVE, ["status", "--format", "json"])
    buckets = {bucket["name"]: bucket["items"] for bucket in json.loads(listed.out)["buckets"]}
    assert len(buckets["Backlog"]) == 5


def test_status_lists_a_backlog_of_one_line_with_no_more_line(tmp_path: Path) -> None:
    assert after(tmp_path, ONE, ["status"]).out == (
        "Backlog (1)\n> S-0001  title 1\nInProgress (0)\nCompleted (0)\n"
    )
