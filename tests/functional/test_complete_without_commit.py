"""The criterion of the development off: a Story is completed without a commit.

A record that holds no `config.toml` has the development off, so the commit is no evidence of
it: `fgraph complete` takes none, of a Task as of the Story. Run end to end through `run` on a
record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, read_config, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0041: fgraph complete still requires --commit"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    *("add", "story", "a title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
STARTED = [ADD_STORY, ADD_TASK, ["start", "S-0001"], ["start", "T-0001"]]
TASK_DONE = ["complete", "T-0001"]
STORY_DONE = ["complete", "S-0001"]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on its files and its configuration."""
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
        load_config=read_config,
    )
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def completed(cwd: Path) -> Outcome:
    """The outcome of completing the Story, its Task completed before it, no commit named."""
    return runs(cwd, *STARTED, TASK_DONE, STORY_DONE)


def test_complete_of_the_story_without_a_commit_exits_with_zero(tmp_path: Path) -> None:
    assert completed(tmp_path).status == 0


def test_status_lists_the_story_under_completed(tmp_path: Path) -> None:
    completed(tmp_path)
    assert fgraph(["status"], tmp_path).out == (
        "Backlog (0)\nInProgress (0)\nCompleted (1)\n  S-0001  a title\n"
    )
