"""The criterion of what a line of status adds: it is on a line of its own right below it.

`fgraph status` and `fgraph watch` list who a blocked item waits on and why, the reason of a removed
one, what it supersedes and what a work item of the Backlog depends on on the line after its own,
beginning under its id, its own line ending with its title. Run end to end on a record in a
temporary directory, through the file adapters of the package, with no git and the development off.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_UNDER = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_FIRST = ["add", "story", "a title", *CRITERION]
ADD_SECOND = ["add", "story", "a second title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
BLOCK_FEATURE = [
    "block",
    "F-0001",
    "--reason",
    "the budget is not agreed",
    "--waiting-on",
    "the sponsor",
]
BLOCK_STORY = ["block", "S-0001", "--reason", "no key", "--waiting-on", "developer"]
BLOCK_TASK = [
    "block",
    "T-0001",
    "--reason",
    "the review is not back",
    "--waiting-on",
    "the reviewer",
]
REMOVE = ["remove", "S-0001", "--reason", "filed by mistake"]
REMOVE_FEATURE = ["remove", "F-0001", "--reason", "filed by mistake"]
SUPERSEDE = ["remove", "S-0001", "--superseded-by", "S-0002", "--reason", "folded in"]
DEPEND = ["amend", "S-0002", "--depends-on", "S-0001"]
STATUS = ["status", "--all"]


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


def below(out: str, item: str, count: int = 2) -> list[str]:
    """The line that names the item and the lines after it, `count` in all."""
    lines = out.splitlines()
    first = next(at for at, line in enumerate(lines) if f" {item} " in line)
    return lines[first : first + count]


def test_a_blocked_feature_waits_on_a_line_below_it(tmp_path: Path) -> None:
    out = runs(
        tmp_path, ADD_FEATURE, ADD_UNDER, ADD_TASK, ["start", "F-0001"], BLOCK_FEATURE, STATUS
    ).out
    assert below(out, "F-0001") == [
        "! F-0001  0/1 W  a feature title",
        "  waiting on the sponsor: the budget is not agreed",
    ]


def test_a_removed_work_item_gives_its_reason_on_a_line_below_it(tmp_path: Path) -> None:
    out = runs(tmp_path, ADD_FIRST, REMOVE, STATUS).out
    assert below(out, "S-0001") == ["  S-0001  a title", "  filed by mistake"]


def test_a_work_item_of_the_backlog_gives_what_it_depends_on_on_a_line_below_it(
    tmp_path: Path,
) -> None:
    out = runs(tmp_path, ADD_FIRST, ADD_SECOND, DEPEND, STATUS).out
    assert below(out, "S-0002") == ["~ S-0002  []  a second title", "  depends on S-0001"]


def test_a_blocked_work_item_waits_on_a_line_below_it_and_above_its_task(tmp_path: Path) -> None:
    started = [ADD_FIRST, ADD_TASK, ["start", "S-0001"], ["start", "T-0001"], BLOCK_STORY]
    out = runs(tmp_path, *started, STATUS).out
    assert below(out, "S-0001", 3) == [
        "! S-0001  0/1 T  a title",
        "  waiting on developer: no key",
        "    => T-0001  a task title",
    ]


def test_a_blocked_task_waits_on_a_line_below_it_under_its_id(tmp_path: Path) -> None:
    started = [ADD_FIRST, ADD_TASK, ["start", "S-0001"], ["start", "T-0001"], BLOCK_TASK]
    out = runs(tmp_path, *started, STATUS).out
    assert below(out, "T-0001") == [
        "    !  T-0001  a task title",
        "       waiting on the reviewer: the review is not back",
    ]


def test_a_superseded_work_item_gives_what_supersedes_it_on_a_line_below_it(
    tmp_path: Path,
) -> None:
    out = runs(tmp_path, ADD_FIRST, ADD_SECOND, SUPERSEDE, STATUS).out
    assert below(out, "S-0001") == ["  S-0001  a title", "  superseded by S-0002, folded in"]


def test_no_line_of_the_listing_holds_two_dashes_before_what_it_adds(tmp_path: Path) -> None:
    out = runs(tmp_path, ADD_FIRST, ADD_SECOND, DEPEND, SUPERSEDE, STATUS).out
    assert [line for line in out.splitlines() if "  -- " in line] == []


def test_watch_lists_a_blocked_feature_with_its_words_on_a_line_below_it(tmp_path: Path) -> None:
    started = [ADD_FEATURE, ADD_UNDER, ADD_TASK, ["start", "F-0001"], BLOCK_FEATURE]
    out = runs(tmp_path, *started, ["watch", "--all", "--count", "1"]).out
    assert below(out, "F-0001") == [
        "! F-0001  0/1 W  a feature title",
        "  waiting on the sponsor: the budget is not agreed",
    ]


def test_a_removed_feature_gives_its_reason_on_a_line_below_it(tmp_path: Path) -> None:
    out = runs(tmp_path, ADD_FEATURE, REMOVE_FEATURE, STATUS).out
    assert below(out, "F-0001") == ["  F-0001  a feature title", "  filed by mistake"]


def test_a_story_of_the_backlog_that_waits_for_nothing_is_one_line(tmp_path: Path) -> None:
    out = runs(tmp_path, ADD_FIRST, ADD_SECOND, STATUS).out
    assert below(out, "S-0001") == ["  S-0001  []  a title", "  S-0002  []  a second title"]


def test_the_json_of_a_blocked_feature_holds_who_it_waits_on(tmp_path: Path) -> None:
    runs(tmp_path, ADD_FEATURE, ADD_UNDER, ADD_TASK, ["start", "F-0001"], BLOCK_FEATURE)
    document = json.loads(fgraph(["status", "--format", "json"], tmp_path).out)
    blocked = next(
        each for b in document["buckets"] for each in b["items"] if each["id"] == "F-0001"
    )
    assert blocked["block"]["waiting_on"] == "the sponsor"
