"""The arguments of status: every item is asked for with `--all`, the top without it."""

import pytest

from flowgraph.parser import build_command_line

pytestmark = pytest.mark.view

PARSER = build_command_line().parser


@pytest.mark.parametrize(
    ("argv", "every"),
    [(["status"], False), (["status", "--all"], True)],
    ids=["the-top", "every-one"],
)
def test_status_asks_for_every_item_with_all_alone(argv: list[str], every: bool) -> None:
    assert PARSER.parse_args(argv).all is every
