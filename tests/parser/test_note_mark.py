"""The options --standing and --open of note: one mark at most, none when neither is given."""

import pytest

from flowgraph.parser.arguments import build_command_line

pytestmark = pytest.mark.edge

NOTE = ["note", "S-0001", "--finding", "t"]


def parsed(argv: list[str]) -> object:
    """The mark of the arguments of the command line, parsed."""
    return build_command_line().parser.parse_args(argv).mark


def test_a_note_with_standing_has_the_mark_standing() -> None:
    assert parsed([*NOTE, "--standing"]) == "standing"


def test_a_note_with_open_has_the_mark_open() -> None:
    assert parsed([*NOTE, "--open"]) == "open"


def test_a_note_with_neither_has_none() -> None:
    assert parsed(NOTE) is None


def test_a_note_with_both_is_refused_by_the_command_line() -> None:
    with pytest.raises(SystemExit):
        parsed([*NOTE, "--standing", "--open"])
