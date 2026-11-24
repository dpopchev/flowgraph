"""The criterion of S-0139: `fgraph status` marks a line without a character to escape.

The line that can start is marked `=` and a started work item whose Tasks are all completed `@`;
a blocked one keeps `!`, a waiting one `~` and a Task being worked `=>`. Run end to end on a
record in a temporary directory, through the file adapters of the package, each command one
second after the one before it, with no git and the development off.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
BLOCK = ["block", "S-0004", "--reason", "no key", "--waiting-on", "developer"]
MARKED = [
    *(["add", "story", f"title {number}", *CRITERION] for number in range(1, 6)),
    *(
        ["add", "task", "a task title", "--parent", f"S-000{story}", "--output", "an output"]
        for story in (3, 4, 5)
    ),
    ["amend", "S-0002", "--depends-on", "S-0001"],
    ["start", "S-0003"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1231"],
    ["start", "S-0004"],
    BLOCK,
    ["start", "S-0005"],
    ["start", "T-0003"],
]


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


def line_of(out: str, item: str) -> str:
    """The line of the output that names the id."""
    return next(line for line in out.splitlines() if item in line)


def indented(out: str) -> list[str]:
    """The lines of the output, each with its indent cut off."""
    return [line.lstrip() for line in out.splitlines()]


class TestStatusOfMarkedLines:
    @pytest.fixture
    def listed(self, tmp_path: Path) -> Outcome:
        return after(tmp_path, MARKED, ["status", "--backlog"])

    def test_status_exits_with_zero(self, listed: Outcome) -> None:
        assert listed.status == 0

    def test_the_line_that_can_start_is_marked_with_an_equals_sign(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0001").startswith("= S-0001")

    def test_the_line_ready_for_review_is_marked_with_an_at_sign(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0003").startswith("@ S-0003")

    def test_no_line_starts_with_a_greater_than_or_a_question_mark(self, listed: Outcome) -> None:
        assert [line for line in indented(listed.out) if line.startswith(("> ", "? "))] == []

    def test_the_line_that_waits_is_marked_with_a_tilde(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0002").startswith("~ S-0002")

    def test_the_blocked_line_is_marked_with_an_exclamation_mark(self, listed: Outcome) -> None:
        assert line_of(listed.out, "S-0004").startswith("! S-0004")

    def test_the_task_being_worked_is_marked_with_an_arrow(self, listed: Outcome) -> None:
        assert line_of(listed.out, "T-0003") == "    => T-0003  a task title"


class TestWatchOfMarkedLines:
    @pytest.fixture
    def watched(self, tmp_path: Path) -> Outcome:
        return after(tmp_path, MARKED, ["watch", "--backlog", "--count", "1"])

    def test_the_line_that_can_start_is_marked_with_an_equals_sign(self, watched: Outcome) -> None:
        assert line_of(watched.out, "S-0001").startswith("= S-0001")

    def test_the_line_ready_for_review_is_marked_with_an_at_sign(self, watched: Outcome) -> None:
        assert line_of(watched.out, "S-0003").startswith("@ S-0003")


class TestStatusAsJsonOfMarkedLines:
    @pytest.fixture
    def document(self, tmp_path: Path) -> dict[str, Any]:
        return json.loads(after(tmp_path, MARKED, ["status", "--format", "json"]).out)

    def test_can_start_names_the_work_item_that_can_start(self, document: dict[str, Any]) -> None:
        assert document["can_start"] == ["S-0001"]

    def test_ready_for_review_names_the_work_item_ready_for_review(
        self, document: dict[str, Any]
    ) -> None:
        assert document["ready_for_review"] == ["S-0003"]

    def test_the_document_holds_no_mark(self, document: dict[str, Any]) -> None:
        assert {"mark", "marks"} & set(document) == set()
