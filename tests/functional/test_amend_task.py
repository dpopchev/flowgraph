"""The criterion of S-0144: fgraph amend rewrites the parts given of a Task in Backlog.

Every part not given stays; a started, a blocked and a completed Task are refused naming the
state. Run end to end on a record in a temporary directory, through the file adapters.
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
ADD_FIRST = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]
ADD_SECOND = ["add", "task", "another task", "--parent", "S-0001", "--output", "another output"]
HOW = ["--description", "how"]
BACKLOG = [ADD_STORY, [*ADD_FIRST, *HOW], [*ADD_SECOND, *HOW]]
STARTED = [*BACKLOG, ["start", "S-0001"], ["start", "T-0001"]]
BLOCKED = [*STARTED, ["block", "T-0001", "--reason", "no key", "--waiting-on", "developer"]]
DONE = [*STARTED, ["complete", "T-0001", "--commit", "abc1234"]]
COMPLETED = [*DONE, ["start", "T-0002"], ["complete", "T-0002", "--commit", "abc1234"]]
ITEM_DONE = [*COMPLETED, ["complete", "S-0001", "--commit", "abc1234"]]
ITEM_REMOVED = [*BACKLOG, ["remove", "S-0001", "--reason", "no longer"]]
ITEM_BLOCKED = [
    *BACKLOG,
    ["start", "S-0001"],
    ["block", "S-0001", "--reason", "r", "--waiting-on", "x"],
]
SHOW = ["show", "S-0001"]
AMEND_FIRST = ["amend", "T-0001", "--title", "a new title"]
AMEND_SECOND = ["amend", "T-0002", "--title", "a new title"]
ONLY_A_TASK = "a Task is amended by its title, its output, its check and its description"
ON = "[development]\nenabled = true\n"
WITH_CHECKS = [
    ADD_STORY,
    [*ADD_FIRST, "--check", "make test"],
    [*ADD_SECOND, "--check", "make test"],
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`; argparse's exit is the status."""
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
            run_check=lambda command, directory: 0,
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def runs(cwd: Path, *argvs: Sequence[str]) -> Outcome:
    """Run each command in cwd in turn; the outcome of the last."""
    outcomes = [fgraph(argv, cwd) for argv in argvs]
    return outcomes[-1]


def development_on(cwd: Path) -> None:
    """Write `[development] enabled = true` as the config.toml of the record of cwd."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    (cwd / ".fgraph" / "config.toml").write_text(ON, encoding="utf-8")


def refusal(outcome: Outcome) -> tuple[int, list[str]]:
    """The exit status and the last line of the error output of a run."""
    return outcome.status, outcome.err.splitlines()[-1:]


def changed(cwd: Path, argvs: Sequence[Sequence[str]], amend: Sequence[str]) -> list[str]:
    """The lines of the show of S-0001 that differ before and after the amend, as now printed."""
    before = runs(cwd, *argvs, SHOW).out.splitlines()
    after = runs(cwd, amend, SHOW).out.splitlines()
    return [new for old, new in zip(before, after, strict=True) if old != new]


def test_amend_names_the_task_and_its_work_item(tmp_path: Path) -> None:
    outcome = runs(tmp_path, *STARTED, AMEND_SECOND)
    assert (outcome.status, outcome.out) == (0, "amended T-0002 of S-0001\n")


@pytest.mark.parametrize(
    ("option", "text", "line"),
    [
        ("--title", "a new title", "  T-0002  a new title"),
        ("--output", "a new output", "    expected output  a new output"),
        ("--description", "why", "    description      why"),
    ],
    ids=["title", "output", "description"],
)
def test_each_part_is_rewritten_alone(option: str, text: str, line: str, tmp_path: Path) -> None:
    assert changed(tmp_path, STARTED, ["amend", "T-0002", option, text]) == [line]


def test_several_parts_are_rewritten_by_one_amend(tmp_path: Path) -> None:
    amend = ["amend", "T-0002", "--title", "a new title", "--output", "a new output"]
    assert changed(tmp_path, STARTED, amend) == [
        "  T-0002  a new title",
        "    expected output  a new output",
    ]


def test_a_blank_description_clears_it(tmp_path: Path) -> None:
    shown = runs(tmp_path, *STARTED, ["amend", "T-0002", "--description", ""], SHOW).out
    assert shown.count("description") == 1


@pytest.mark.parametrize(
    ("argvs", "state"),
    [
        (STARTED, "T-0001 is started already"),
        (BLOCKED, "T-0001 is blocked"),
        (COMPLETED, "T-0001 is completed already"),
        (ITEM_DONE, "T-0001 is completed already"),
        (ITEM_REMOVED, "S-0001 is removed already"),
    ],
    ids=["started", "blocked", "completed", "of-a-completed-item", "of-a-removed-item"],
)
def test_a_task_that_is_not_in_backlog_is_refused_naming_its_state(
    argvs: list[list[str]], state: str, tmp_path: Path
) -> None:
    assert refusal(runs(tmp_path, *argvs, AMEND_FIRST)) == (2, [f"fgraph: error: {state}"])


@pytest.mark.parametrize(
    "argvs", [BACKLOG, ITEM_BLOCKED], ids=["of-a-work-item-in-backlog", "of-a-blocked-work-item"]
)
def test_a_task_in_backlog_of_a_work_item_in_backlog_or_blocked_is_amended(
    argvs: list[list[str]], tmp_path: Path
) -> None:
    assert runs(tmp_path, *argvs, AMEND_SECOND).status == 0


@pytest.mark.parametrize(
    ("amend", "error"),
    [
        (["amend", "T-0002"], "amend rewrites no part of T-0002: name one"),
        (["amend", "T-0002", "--title", ""], "title is empty"),
        (["amend", "T-0002", "--output", " "], "output is empty"),
        (["amend", "T-0009", "--title", "x"], "no Task T-0009 in the record"),
        (["amend", "T-0002", "--then", "x"], f"T-0002 has no then: {ONLY_A_TASK}"),
        (["amend", "T-0002", "--parent", "none"], f"T-0002 has no parent: {ONLY_A_TASK}"),
        (["amend", "T-0002", "--criterion", "x"], f"T-0002 has no criteria: {ONLY_A_TASK}"),
        (
            ["amend", "S-0002", "--output", "x"],
            "S-0002 has no output: only a Task states them",
        ),
        (
            ["amend", "F-0001", "--output", "x"],
            "F-0001 has no output: a Feature is amended by its title, its description and its"
            " criteria",
        ),
    ],
    ids=[
        "no-part",
        "blank-title",
        "blank-output",
        "unknown-task",
        "then",
        "parent",
        "criterion",
        "output-of-a-story",
        "output-of-a-feature",
    ],
)
def test_an_amend_refused_exits_with_two_and_names_why(
    amend: list[str], error: str, tmp_path: Path
) -> None:
    others = [
        ["add", "story", "another", *CRITERION],
        ["add", "feature", "a feature", "--criterion", "c"],
    ]
    assert refusal(runs(tmp_path, *BACKLOG, *others, amend)) == (2, [f"fgraph: error: {error}"])


def test_an_amend_refused_leaves_the_work_item_as_it_was(tmp_path: Path) -> None:
    before = runs(tmp_path, *STARTED, SHOW).out
    assert runs(tmp_path, AMEND_FIRST, SHOW).out == before


class TestTheCheckOfATask:
    @pytest.fixture
    def amended(self, tmp_path: Path) -> Outcome:
        development_on(tmp_path)
        return runs(tmp_path, *WITH_CHECKS, ["amend", "T-0001", "--check", "make lint"], SHOW)

    def test_show_lists_the_check_amended(self, amended: Outcome) -> None:
        assert "    check            make lint\n" in amended.out

    def test_an_amend_of_the_title_keeps_the_check_line(self, tmp_path: Path) -> None:
        development_on(tmp_path)
        assert changed(tmp_path, WITH_CHECKS, AMEND_FIRST) == ["  T-0001  a new title"]

    def test_a_blank_check_is_refused(self, tmp_path: Path) -> None:
        development_on(tmp_path)
        outcome = runs(tmp_path, *WITH_CHECKS, ["amend", "T-0001", "--check", ""])
        assert refusal(outcome) == (2, ["fgraph: error: check is empty"])

    def test_a_check_with_the_development_off_is_refused(self, tmp_path: Path) -> None:
        outcome = runs(tmp_path, *BACKLOG, ["amend", "T-0002", "--check", "make lint"])
        assert refusal(outcome) == (
            2,
            [
                "fgraph: error: a Task takes no --check: the development is off"
                f" -- set development.enabled = true in {tmp_path}/.fgraph/config.toml"
            ],
        )
