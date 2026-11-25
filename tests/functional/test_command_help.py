"""The criterion of the help of a command: `fgraph start --help` prints its usage and options.

Run through `run` in a directory that holds no record: the help of a command needs none.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

import pytest

from flowgraph.cli import run

pytestmark = pytest.mark.functional

COMMANDS = [
    ("init",),
    ("add",),
    ("add", "story"),
    ("add", "task"),
    ("add", "upkeep"),
    ("add", "bug"),
    ("add", "spike"),
    ("add", "feature"),
    ("add", "term"),
    ("amend",),
    ("show",),
    ("about",),
    ("brief",),
    ("goal",),
    ("start",),
    ("hand",),
    ("commit",),
    ("block",),
    ("unblock",),
    ("complete",),
    ("land",),
    ("release",),
    ("sync",),
    ("note",),
    ("verify",),
    ("knowledge",),
    ("terms",),
    ("graph",),
    ("remove",),
    ("reorder",),
    ("status",),
    ("watch",),
    ("config",),
    ("config", "show"),
    ("config", "set"),
]


def never(*_: object) -> Never:
    """The store or the git work tree of a record, which the help of a command never opens."""
    raise AssertionError("the help of a command opens no record")


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str]) -> Outcome:
    """Run the command in a directory that holds no record."""
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        Path("/work"),
        lambda _: False,
        out.append,
        err.append,
        open_store=never,
        open_git=never,
        now=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    return Outcome(status, "".join(out), "".join(err))


class TestTheHelpOfStartInAnyDirectory:
    @pytest.fixture
    def helped(self) -> Outcome:
        return fgraph(["start", "--help"])

    def test_exits_with_zero(self, helped: Outcome) -> None:
        assert helped.status == 0

    def test_prints_the_usage_of_start(self, helped: Outcome) -> None:
        assert helped.out.splitlines()[0] == (
            "usage: fgraph start [-h] [--slug TEXT] [--agent NAME] [ID]"
        )

    def test_prints_the_options_of_start(self, helped: Outcome) -> None:
        assert [line.split()[0:2] for line in helped.out.splitlines() if "--" in line][1:] == [
            ["-h,", "--help"],
            ["--slug", "TEXT"],
            ["--agent", "NAME"],
        ]

    def test_names_the_feature_among_the_ids_start_takes(self, helped: Outcome) -> None:
        positional = helped.out.split("options:")[0].split("positional arguments:")[-1]
        assert " ".join(positional.split()) == (
            "ID the id of the work item, of the Task or of the Feature; left out, the first"
            " line of the Backlog that can start"
        )

    def test_says_the_slug_names_the_branch_of_a_work_item_or_of_the_first_of_a_feature(
        self, helped: Outcome
    ) -> None:
        before_the_agent = helped.out.split("  --agent NAME")[0]
        assert " ".join(before_the_agent.split("--slug TEXT")[-1].split()) == (
            "the words of a work item's branch after its id, instead of its title's first four;"
            " of a Feature, those of its first work item; read with the development on"
        )

    def test_writes_nothing_on_the_error_output(self, helped: Outcome) -> None:
        assert helped.err == ""


@pytest.mark.parametrize("command", COMMANDS, ids=[" ".join(command) for command in COMMANDS])
def test_every_command_prints_its_own_usage_and_exits_with_zero(command: tuple[str, ...]) -> None:
    outcome = fgraph([*command, "--help"])
    assert (outcome.status, outcome.out.split("[")[0]) == (
        0,
        f"usage: fgraph {' '.join(command)} ",
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["start", "-h"],
        ["start", "S-0001", "--help"],
        ["start", "--slug", "a-slug", "--help"],
        ["--dir", "elsewhere", "start", "--help"],
    ],
    ids=["short", "after-its-argument", "after-an-option", "after-dir"],
)
def test_the_help_of_a_command_is_printed_wherever_the_option_stands(argv: list[str]) -> None:
    outcome = fgraph(argv)
    assert (outcome.status, outcome.out.splitlines()[:1]) == (
        0,
        ["usage: fgraph start [-h] [--slug TEXT] [--agent NAME] [ID]"],
    )


def test_the_help_of_add_lists_the_kinds() -> None:
    listed = fgraph(["add", "--help"]).out.splitlines()
    kinds = [line for line in listed if line.startswith("    ") and line[4] != " "]
    assert [line.split()[0] for line in kinds] == [
        "story",
        "task",
        "upkeep",
        "bug",
        "spike",
        "feature",
        "term",
    ]


def test_the_help_menu_says_a_landing_runs_its_gate() -> None:
    menu = " ".join(fgraph(["--help"]).out.split())
    summary = menu.split(" land ", 1)[1].split(" remove ", 1)[0]
    assert summary == (
        "land a started work item on main: merge its branch, run its gate and complete it"
    )


def test_the_help_menu_says_a_remove_takes_a_work_item_a_task_or_a_feature() -> None:
    menu = " ".join(fgraph(["--help"]).out.split())
    summary = menu.split(" remove ", 1)[1].split(" note ", 1)[0]
    assert summary == "remove a work item, a Task or a Feature, kept with its reason"


def test_the_help_of_reorder_names_the_feature_beside_the_work_item() -> None:
    helped = fgraph(["reorder", "--help"]).out.splitlines()
    assert [line for line in helped if line.startswith(("  ID ", "  --before"))] == [
        "  ID           the id of the work item or of the Feature to move",
        "  --before ID  the work item or the Feature it is listed right above",
    ]


def test_the_help_of_release_names_the_version_it_may_be_given() -> None:
    helped = fgraph(["release", "--help"]).out.splitlines()
    assert [line.split()[0:2] for line in helped if line.startswith("  -")] == [
        ["-h,", "--help"],
        ["--version", "VERSION"],
    ]


def test_the_help_menu_says_reorder_puts_a_work_item_or_a_feature_before_another() -> None:
    menu = " ".join(fgraph(["--help"]).out.split())
    summary = menu.split(" reorder ", 1)[1].split(" status ", 1)[0]
    assert summary == "put a work item or a Feature of the Backlog before another"
