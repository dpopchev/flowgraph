"""The option --supersedes of note: once per line it supersedes, none when it is not given."""

import pytest

from flowgraph.parser.arguments import build_command_line

pytestmark = pytest.mark.edge

NOTE = ["note", "S-0001", "--decision", "t"]


def parsed(argv: list[str]) -> object:
    """The refs --supersedes names in the arguments of the command line, parsed."""
    return build_command_line().parser.parse_args(argv).supersedes


def test_a_note_with_supersedes_given_twice_has_both_refs() -> None:
    assert parsed([*NOTE, "--supersedes", "S-0001#1", "--supersedes", "S-0001#2"]) == [
        "S-0001#1",
        "S-0001#2",
    ]


def test_a_note_without_supersedes_has_none() -> None:
    assert parsed(NOTE) is None
