"""The criterion of a Feature marked blocked: `fgraph status` marks it by a blocked Task.

The line of a started Feature whose started Story holds a blocked Task starts with `!` and ends
with what that Task waits on; a started Task beside the blocked one does not lift the mark. Run
end to end on a record in a temporary directory, through the file adapters of the package, each
command one second after the one before it.
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
ADD_OTHER = ["add", "task", "another task", "--parent", "S-0001", "--output", "an output"]
BLOCK = ["block", "T-0001", "--reason", "the review is not back", "--waiting-on", "the reviewer"]
ADDED = (ADD_FEATURE, ADD_STORY, ADD_TASK, ADD_OTHER)
BLOCKED = (*ADDED, ["start", "F-0001"], ["start", "T-0001"], BLOCK)
MARKED = "! F-0001  0/1 W  a feature title\n  waiting on the reviewer: the review is not back"


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


def test_status_marks_a_started_feature_whose_started_story_holds_a_blocked_task(
    tmp_path: Path,
) -> None:
    assert status_after(tmp_path, *BLOCKED).out == (
        "backlog (0)\n"
        "in-progress (1)\n"
        f"{MARKED}\n"
        "    S-0001  0/2 T  a title\n"
        "      !  T-0001  a task title\n"
        "         waiting on the reviewer: the review is not back\n"
        "completed (0)\n"
    )


def test_a_started_task_beside_the_blocked_one_does_not_lift_the_mark_of_the_feature(
    tmp_path: Path,
) -> None:
    assert status_after(tmp_path, *BLOCKED, ["start", "T-0002"]).out.splitlines()[2:7] == [
        *MARKED.splitlines(),
        "    S-0001  0/2 T  a title",
        "      !  T-0001  a task title",
        "         waiting on the reviewer: the review is not back",
    ]
