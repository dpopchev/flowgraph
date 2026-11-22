"""The criterion of a Feature in its bucket: `fgraph status` lists it in place of its work items.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0050: a Feature is listed above the buckets yet"),
]

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_ALONE = ["add", "story", "a title that stands alone", *CRITERION]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = ["add", "story", "a title", *CRITERION, "--parent", "F-0001"]
ADD_OTHER = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]


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


def test_status_lists_the_story_then_the_feature_with_its_progress_and_neither_story_of_it(
    tmp_path: Path,
) -> None:
    listed = status_after(tmp_path, ADD_ALONE, ADD_FEATURE, ADD_STORY, ADD_OTHER)
    assert listed.out == (
        "Backlog (2)\n"
        "  S-0001  a title that stands alone\n"
        "  F-0001  0/2 W  a feature title\n"
        "InProgress (0)\n"
        "Completed (0)\n"
    )
