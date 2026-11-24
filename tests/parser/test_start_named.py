"""The id of a start given none: the top is read for it, and the arguments are kept otherwise."""

import argparse

import pytest

from flowgraph.parser.arguments import build_command_line
from flowgraph.parser.ids import ids_read
from flowgraph.parser.start import start_named
from flowgraph.status.top import NothingToStartError

pytestmark = pytest.mark.view


def parse(argv: list[str]) -> argparse.Namespace:
    """The arguments of the command line, parsed as the command line parses them."""
    return build_command_line().parser.parse_args(argv)


def read(argv: list[str]) -> dict[str, object]:
    """The arguments of the command line, parsed and read through ids_read."""
    return vars(ids_read(parse(argv)))


def never() -> str:
    """A top that a start given an id, or a command that is no start, never asks for."""
    raise AssertionError("the top is read for a start given no id only")


def raising() -> str:
    """A top of a Backlog that no line of which can start."""
    raise NothingToStartError("nothing to start: the Backlog is empty")


def test_a_start_alone_reads_to_no_id() -> None:
    assert read(["start"])["id"] is None


def test_a_start_with_a_slug_reads_no_id_and_the_slug() -> None:
    args = read(["start", "--slug", "a-slug"])
    assert (args["id"], args["slug"]) == (None, "a-slug")


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["start", "s2"], id="id-after-the-command"),
        pytest.param(["start", "--agent", "x", "s2"], id="id-after-an-option"),
        pytest.param(["start", "s2", "--slug", "a"], id="id-before-an-option"),
    ],
)
def test_the_id_is_read_wherever_it_stands(argv: list[str]) -> None:
    assert read(argv)["id"] == "S-0002"


def test_the_usage_of_start_ends_in_an_optional_id() -> None:
    usage = build_command_line().commands[("start",)].format_usage()
    assert usage == "usage: fgraph start [-h] [--slug TEXT] [--agent NAME] [ID]\n"


def test_a_start_given_no_id_takes_the_top() -> None:
    assert start_named(parse(["start"]), lambda: "S-0002").id == "S-0002"


def test_a_start_given_no_id_keeps_its_slug_and_agent() -> None:
    args = parse(["start", "--slug", "a-slug", "--agent", "sonnet-a1"])
    named = start_named(args, lambda: "S-0002")
    assert (named.slug, named.agent) == ("a-slug", "sonnet-a1")


def test_the_arguments_given_still_hold_no_id_after_the_top_is_read() -> None:
    args = parse(["start"])
    start_named(args, lambda: "S-0002")
    assert args.id is None


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["start", "S-0001"], id="a-start-that-names-its-id"),
        pytest.param(["status"], id="a-status"),
        pytest.param(["show", "S-0001"], id="a-show"),
    ],
)
def test_arguments_that_need_no_top_come_back_as_they_are(argv: list[str]) -> None:
    args = parse(argv)
    assert start_named(args, never) is args


def test_a_top_that_raises_the_refusal_of_a_start_goes_up() -> None:
    with pytest.raises(NothingToStartError):
        start_named(parse(["start"]), raising)
