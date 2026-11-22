"""The arguments of status: the format of its output, text unless json is asked for."""

import pytest

from flowgraph.parser import build_command_line

pytestmark = pytest.mark.view

PARSER = build_command_line().parser


@pytest.mark.parametrize(
    ("argv", "format_"),
    [
        (["status"], "text"),
        (["status", "--format", "json"], "json"),
        (["status", "--format", "xml"], "xml"),
    ],
    ids=["text-by-default", "json", "any-word-is-parsed"],
)
def test_status_asks_for_the_format_it_is_given(argv: list[str], format_: str) -> None:
    assert PARSER.parse_args(argv).format == format_
