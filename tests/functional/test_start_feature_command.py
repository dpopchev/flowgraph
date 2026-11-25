"""The criterion of S-0079: the refusal of a start under a Feature not started names its way out.

Run end to end through `run` on a record in a temporary directory, through the file adapters of
the package; no git is opened.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_STORY = [
    "add",
    "story",
    "a title",
    "--given",
    "a state",
    "--when",
    "an action",
    "--then",
    "another",
    "--parent",
    "F-0001",
]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
RECORD = (ADD_FEATURE, ADD_STORY, ADD_TASK)
START_STORY = ["start", "S-0001"]
START_FEATURE = ["start", "F-0001"]
XFAIL = pytest.mark.xfail(
    strict=True, reason="S-0079: the refusal names the Feature, not the command that starts it"
)


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


@XFAIL
def test_the_start_of_a_story_under_a_feature_not_started_names_the_command_that_starts_it(
    tmp_path: Path,
) -> None:
    """The refusal of the start names fgraph start F-0001 as the way past it."""
    outcome = runs(tmp_path, *RECORD, START_STORY)
    last_line = (
        "fgraph: error: S-0001 cannot start: F-0001 is not started: fgraph start F-0001 starts it"
    )
    assert (outcome.status, outcome.err.splitlines()[-1:]) == (2, [last_line])


def test_the_command_the_refusal_names_starts_the_feature(tmp_path: Path) -> None:
    """The command the refusal names starts the Feature, then the Story starts under it."""
    outcome = runs(tmp_path, *RECORD, START_STORY, START_FEATURE)
    assert (outcome.status, outcome.out) == (0, "started F-0001 with S-0001\n")
