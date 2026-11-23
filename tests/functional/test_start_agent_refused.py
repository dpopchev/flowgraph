"""The refusals of --agent at a start: a Task, a name that is no agent, the development off.

Each exits with two and writes nothing. Run end to end on a record in a temporary directory,
through the file adapters of the package and its configuration.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
IN_FEATURE = ["add", "story", "another title", *CRITERION, "--parent", "F-0001"]
TASK_IN_FEATURE = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
SETUP = (ADD_STORY, ADD_TASK)
NO_AGENT = (
    "fgraph: error: {name!r} is no agent: it is one word of at most 32 letters, digits and"
    " . _ : / -"
)
OFF = (
    "fgraph: error: {item} takes no --agent: the development is off, so no agent is handed work"
    " -- set development.enabled = true in {config}"
)


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
            load_config=read_config,
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def record_text(cwd: Path) -> dict[str, str]:
    """The text of every file of the items of the record in cwd, by name."""
    files = (cwd / ".fgraph" / "items").glob("*.toml")
    return {file.name: file.read_text(encoding="utf-8") for file in files}


def turn_development_on(project: Path) -> None:
    """Write `[development] enabled = true` as the config.toml of the record of the project."""
    record = project / ".fgraph"
    record.mkdir(exist_ok=True)
    (record / "config.toml").write_text("[development]\nenabled = true\n", encoding="utf-8")


CASES = [
    pytest.param(
        True,
        [*SETUP, ["start", "S-0001"]],
        ["start", "T-0001", "--agent", "sonnet-a1"],
        "fgraph: error: --agent names the agent of a work item: T-0001 is a Task",
        id="a-task",
    ),
    pytest.param(
        True,
        [*SETUP],
        ["start", "S-0001", "--agent", "two words"],
        NO_AGENT.format(name="two words"),
        id="a-name-with-a-space",
    ),
    pytest.param(
        True,
        [*SETUP],
        ["start", "S-0001", "--agent", "a" * 33],
        NO_AGENT.format(name="a" * 33),
        id="a-name-too-long",
    ),
    pytest.param(
        True,
        [*SETUP],
        ["start", "S-0001", "--agent", ""],
        NO_AGENT.format(name=""),
        id="an-empty-name",
    ),
    pytest.param(
        False,
        [*SETUP],
        ["start", "S-0001", "--agent", "sonnet-a1"],
        OFF.format(item="S-0001", config="{config}"),
        id="the-development-off",
    ),
    pytest.param(
        False,
        [ADD_FEATURE, IN_FEATURE, TASK_IN_FEATURE],
        ["start", "F-0001", "--agent", "sonnet-a1"],
        OFF.format(item="F-0001", config="{config}"),
        id="a-feature-with-the-development-off",
    ),
]


@pytest.mark.parametrize(("on", "setup", "refused", "error"), CASES)
def test_a_start_refused_exits_with_two_and_names_why(
    on: bool, setup: list[list[str]], refused: list[str], error: str, tmp_path: Path
) -> None:
    if on:
        turn_development_on(tmp_path)
    outcome = runs(tmp_path, *setup, refused)
    expected = error.format(config=tmp_path / ".fgraph" / "config.toml")
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, expected)


@pytest.mark.parametrize(("on", "setup", "refused", "error"), CASES)
def test_a_start_refused_writes_nothing(
    on: bool, setup: list[list[str]], refused: list[str], error: str, tmp_path: Path
) -> None:
    if on:
        turn_development_on(tmp_path)
    runs(tmp_path, *setup)
    before = record_text(tmp_path)
    fgraph(refused, tmp_path)
    assert record_text(tmp_path) == before
