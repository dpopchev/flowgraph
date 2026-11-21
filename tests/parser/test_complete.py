"""The arguments of complete: the commit that holds the work is given with `--commit`, or not."""

import pytest

from flowgraph.parser import build_command_line

pytestmark = pytest.mark.view

COMMAND_LINE = build_command_line()


@pytest.mark.parametrize(
    ("argv", "commit"),
    [(["complete", "S-0001"], None), (["complete", "S-0001", "--commit", "abc1234"], "abc1234")],
    ids=["none", "a-commit"],
)
def test_complete_takes_the_commit_given_or_none(argv: list[str], commit: str | None) -> None:
    assert COMMAND_LINE.parser.parse_args(argv).commit == commit


def test_the_help_of_complete_says_when_the_commit_is_needed() -> None:
    helped = " ".join(COMMAND_LINE.commands["complete",].format_help().split())
    assert "--commit SHA the commit that holds its work: needed with the development on" in helped
