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
    ("add",),
    ("add", "story"),
    ("add", "task"),
    ("add", "upkeep"),
    ("add", "bug"),
    ("add", "spike"),
    ("add", "feature"),
    ("amend",),
    ("show",),
    ("start",),
    ("block",),
    ("unblock",),
    ("complete",),
    ("land",),
    ("remove",),
    ("reorder",),
    ("status",),
    ("watch",),
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
        assert helped.out.splitlines()[0] == "usage: fgraph start [-h] [--slug TEXT] ID"

    def test_prints_the_options_of_start(self, helped: Outcome) -> None:
        assert [line.split()[0:2] for line in helped.out.splitlines() if "--" in line][1:] == [
            ["-h,", "--help"],
            ["--slug", "TEXT"],
        ]

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
        ["usage: fgraph start [-h] [--slug TEXT] ID"],
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
    ]
