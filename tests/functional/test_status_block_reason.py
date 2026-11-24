"""The criterion of S-0084: `fgraph status` names the reason of a block beside what it waits on.

The line of a Task blocked with the reason `no key`, waiting on `developer`, and the line of a
blocked Feature, each end with what it waits on, a colon and the reason. Run end to end on a
record in a temporary directory, through the file adapters of the package, each command one
second after the one before it.
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
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADDED = (ADD_FEATURE, ADD_STORY, ADD_TASK)
BLOCK_TASK = ["block", "T-0001", "--reason", "no key", "--waiting-on", "developer"]
BLOCK_FEATURE = ["block", "F-0001", "--reason", "no budget", "--waiting-on", "sponsor"]
TASK_BLOCKED = (*ADDED, ["start", "F-0001"], ["start", "T-0001"], BLOCK_TASK)
FEATURE_BLOCKED = (*ADDED, ["start", "F-0001"], BLOCK_FEATURE)


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


def status_after(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd a second after the last, then `fgraph status`; its outcome."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    return fgraph(["status"], cwd, START + timedelta(seconds=len(argvs)))


def test_status_exits_with_zero_on_a_record_with_a_blocked_task(tmp_path: Path) -> None:
    assert status_after(tmp_path, *TASK_BLOCKED).status == 0


def test_the_line_of_a_blocked_task_names_its_reason_beside_what_it_waits_on(
    tmp_path: Path,
) -> None:
    assert status_after(tmp_path, *TASK_BLOCKED).out.splitlines()[5:7] == [
        "      !  T-0001  a task title",
        "         waiting on developer: no key",
    ]


def test_the_line_of_a_blocked_feature_names_its_reason_beside_what_it_waits_on(
    tmp_path: Path,
) -> None:
    assert status_after(tmp_path, *FEATURE_BLOCKED).out.splitlines()[2:4] == [
        "! F-0001  0/1 W  a feature title",
        "  waiting on sponsor: no budget",
    ]
