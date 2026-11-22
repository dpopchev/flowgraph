"""The kinds fgraph verify takes and what it refuses: exit 2 and nothing written.

It takes a completed Story, Bug or Upkeep, once, with exactly one of the answers yes and no.
Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run
from tests.functional.completed_story import ADD_STORY, ADD_TASK, CRITERION, STANDING_ALONE

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TEXT = "make check: all checks passed"
TAKES = "fgraph verify takes a completed Story, Bug or Upkeep"
ADD_BUG = ["add", "bug", "a bug title", "--observed", "it fails", "--expected", "it works"]
ADD_UPKEEP = ["add", "upkeep", "an upkeep title", *CRITERION]
ADD_SPIKE = ["add", "spike", "a spike title", "--hypothesis", "Can one file hold it?"]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]


def started(add: Sequence[str], parent: str) -> tuple[Sequence[str], ...]:
    """The commands that leave the work item the add makes started, its Task T-0001 completed."""
    task = ["add", "task", "a task title", "--parent", parent, "--output", "an output"]
    task_done = ["complete", "T-0001", "--commit", "abc1234"]
    return (add, task, ["start", parent], ["start", "T-0001"], task_done)


def standing_alone(add: Sequence[str], parent: str) -> tuple[Sequence[str], ...]:
    """The commands that leave the work item the add makes completed, its Task T-0001."""
    return (*started(add, parent), ["complete", parent, "--commit", "def5678"])


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


@pytest.mark.parametrize(
    ("add", "item"),
    [(ADD_BUG, "B-0001"), (ADD_UPKEEP, "U-0001")],
    ids=["a-bug", "an-upkeep"],
)
def test_a_completed_bug_and_a_completed_upkeep_keep_the_answer(
    tmp_path: Path, add: list[str], item: str
) -> None:
    runs(tmp_path, *standing_alone(add, item))
    fgraph(["verify", item, "--yes", TEXT], tmp_path)
    assert f"  verified     yes  2026-01-01  {TEXT}\n" in fgraph(["show", item], tmp_path).out


@pytest.mark.parametrize(
    ("setup", "item", "message"),
    [
        ((ADD_STORY, ADD_TASK), "S-0001", f"S-0001 is backlog: {TAKES}"),
        (started(ADD_STORY, "S-0001"), "S-0001", f"S-0001 is started: {TAKES}"),
        ((ADD_FEATURE,), "F-0001", f"'F-0001' is no work item id: {TAKES}"),
        (STANDING_ALONE, "T-0001", f"'T-0001' is no work item id: {TAKES}"),
        ((ADD_STORY,), "S-0009", "no Story S-0009 in the record"),
    ],
    ids=["not-completed", "started", "a-feature", "a-task", "no-such-item"],
)
def test_verify_of_what_it_does_not_take_exits_with_two_and_names_what_it_takes(
    tmp_path: Path, setup: tuple[Sequence[str], ...], item: str, message: str
) -> None:
    runs(tmp_path, *setup)
    outcome = fgraph(["verify", item, "--yes", TEXT], tmp_path)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (2, f"fgraph: error: {message}")


def test_a_completed_spike_is_refused(tmp_path: Path) -> None:
    complete = ["complete", "Q-0001", "--commit", "def5678", "--decision", "yes, one file"]
    runs(tmp_path, *started(ADD_SPIKE, "Q-0001"), complete)
    outcome = fgraph(["verify", "Q-0001", "--yes", TEXT], tmp_path)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (
        2,
        f"fgraph: error: Q-0001 is a Spike: {TAKES}",
    )


def test_a_second_answer_is_refused_and_the_first_stays(tmp_path: Path) -> None:
    runs(tmp_path, *STANDING_ALONE, ["verify", "S-0001", "--yes", TEXT])
    second = fgraph(["verify", "S-0001", "--yes", "another text"], tmp_path)
    shown = fgraph(["show", "S-0001"], tmp_path).out
    assert (second.status, TEXT in shown, "another text" in shown) == (2, True, False)


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["verify", "S-0001"], "one of the arguments --yes --no is required"),
        (
            ["verify", "S-0001", "--yes", TEXT, "--no", "it fails"],
            "argument --no: not allowed with argument --yes",
        ),
    ],
    ids=["neither-answer", "both-answers"],
)
def test_verify_without_exactly_one_answer_exits_with_two_naming_both(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], argv: list[str], message: str
) -> None:
    runs(tmp_path, *STANDING_ALONE)
    with pytest.raises(SystemExit) as exited:
        fgraph(argv, tmp_path)
    error = capsys.readouterr().err.splitlines()[-1]
    assert (exited.value.code, error) == (2, f"fgraph verify: error: {message}")


def test_a_no_after_a_yes_is_refused_and_the_yes_stays(tmp_path: Path) -> None:
    runs(tmp_path, *STANDING_ALONE, ["verify", "S-0001", "--yes", TEXT])
    second = fgraph(["verify", "S-0001", "--no", "it fails"], tmp_path)
    shown = fgraph(["show", "S-0001"], tmp_path).out
    assert (second.status, f"verified     yes  2026-01-01  {TEXT}" in shown) == (2, True)


def test_a_no_refused_adds_no_bug(tmp_path: Path) -> None:
    runs(tmp_path, ADD_STORY, ADD_TASK, ["verify", "S-0001", "--no", "it fails"])
    assert not (tmp_path / ".fgraph" / "items" / "B-0001.toml").exists()


def test_a_blank_text_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    runs(tmp_path, *STANDING_ALONE)
    outcome = fgraph(["verify", "S-0001", "--yes", " "], tmp_path)
    assert (outcome.status, "verified" in fgraph(["show", "S-0001"], tmp_path).out) == (2, False)
