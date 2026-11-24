"""The criterion of S-0131: a work item of the Backlog is listed with its count of Tasks.

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


def story(number: int) -> list[str]:
    """The command that adds the Story of that number."""
    return ["add", "story", f"title {number}", *CRITERION]


def task(parent: str) -> list[str]:
    """The command that adds a Task under that parent."""
    return ["add", "task", "a task title", "--parent", parent, "--output", "an output"]


HELD = [story(1), story(2), task("S-0001"), task("S-0001"), task("S-0001")]
WAITS = [*HELD, ["amend", "S-0002", "--depends-on", "S-0001"]]
UNDER = [
    ["add", "feature", "a feature title", "--criterion", "a criterion"],
    [*story(1), "--parent", "F-0001"],
]
MOVED = [
    story(1),
    story(2),
    task("S-0001"),
    task("S-0002"),
    ["start", "S-0001"],
    ["start", "S-0002"],
    ["start", "T-0002"],
    ["complete", "T-0002", "--commit", "abc1234"],
    ["complete", "S-0002", "--commit", "abc1234"],
]


def test_status_backlog_lists_the_count_of_tasks_in_brackets(tmp_path: Path) -> None:
    listed = after(tmp_path, HELD, ["status", "--backlog"])
    assert listed.out.splitlines()[:3] == [
        "backlog (2)",
        "> S-0001  [3 T]  title 1",
        "  S-0002  []  title 2",
    ]


def test_a_plain_status_lists_the_count_of_tasks_in_brackets(tmp_path: Path) -> None:
    listed = after(tmp_path, HELD, ["status"])
    assert listed.out.splitlines()[1:3] == [
        "> S-0001  [3 T]  title 1",
        "  ... 1 more, 0 can start",
    ]


def test_watch_lists_the_count_of_tasks_in_brackets(tmp_path: Path) -> None:
    listed = after(tmp_path, HELD, ["watch", "--backlog", "--count", "1"])
    assert listed.out.splitlines()[:3] == [
        "backlog (2)",
        "> S-0001  [3 T]  title 1",
        "  S-0002  []  title 2",
    ]


def test_a_line_that_waits_keeps_its_mark_and_its_words(tmp_path: Path) -> None:
    listed = after(tmp_path, WAITS, ["status", "--backlog"])
    assert listed.out.splitlines()[2:4] == ["~ S-0002  []  title 2", "  depends on S-0001"]


def test_a_feature_keeps_its_count_of_work_items_and_gains_no_brackets(tmp_path: Path) -> None:
    listed = after(tmp_path, UNDER, ["status"])
    assert "> F-0001  0/1 W  a feature title" in listed.out.splitlines()


def test_a_started_work_item_reads_as_before(tmp_path: Path) -> None:
    listed = after(tmp_path, MOVED, ["status"])
    assert "  S-0001  0/1 T  title 1" in listed.out.splitlines()


def test_a_completed_work_item_reads_as_before(tmp_path: Path) -> None:
    listed = after(tmp_path, MOVED, ["status"])
    assert "  S-0002  abc1234  title 2" in listed.out.splitlines()


def test_the_json_gives_the_progress_of_the_work_item_unchanged(tmp_path: Path) -> None:
    listed = after(tmp_path, HELD, ["status", "--format", "json"])
    items = json.loads(listed.out)["buckets"][0]["items"]
    assert items[0]["progress"] == {"completed": 0, "total": 3}
