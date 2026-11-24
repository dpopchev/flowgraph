"""The option --live of knowledge: it lists the live lines alone, and knowledge alone lists every line."""

import pytest

from flowgraph.parser.arguments import build_command_line

pytestmark = pytest.mark.edge


def live_of(argv: list[str]) -> bool:
    """Whether the arguments of the command line ask for the live lines alone."""
    return build_command_line().parser.parse_args(argv).live


def test_knowledge_with_live_asks_for_the_live_lines_alone() -> None:
    assert live_of(["knowledge", "--live"]) is True


def test_knowledge_alone_asks_for_every_line() -> None:
    assert live_of(["knowledge"]) is False
