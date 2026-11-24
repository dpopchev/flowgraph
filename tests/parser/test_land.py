"""The arguments of land: the message of the commit it makes is given with `--message`, or not."""

import pytest

from flowgraph.parser import build_command_line

pytestmark = pytest.mark.view

COMMAND_LINE = build_command_line()


@pytest.mark.parametrize(
    ("argv", "message"),
    [(["land", "S-0001"], None), (["land", "S-0001", "--message", "feat: land"], "feat: land")],
    ids=["none", "a-message"],
)
def test_land_takes_the_message_given_or_none(argv: list[str], message: str | None) -> None:
    assert COMMAND_LINE.parser.parse_args(argv).message == message


def test_the_help_of_land_says_when_the_message_is_needed() -> None:
    helped = " ".join(COMMAND_LINE.commands["land",].format_help().split())
    assert (
        "--message TEXT the message of the commit the landing makes:"
        " needed unless it lands by fast-forward"
    ) in helped


@pytest.mark.parametrize(
    ("argv", "approved"),
    [(["land", "S-0001"], False), (["land", "S-0001", "--approved"], True)],
    ids=["not-given", "given"],
)
def test_land_takes_approved_given_or_not(argv: list[str], approved: bool) -> None:
    assert COMMAND_LINE.parser.parse_args(argv).approved is approved


def test_the_help_of_land_names_the_approver_key() -> None:
    helped = " ".join(COMMAND_LINE.commands["land",].format_help().split())
    assert "development.approver = developer" in helped
