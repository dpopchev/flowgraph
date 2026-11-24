"""The option --realizes of add and amend: its text is read as typed, refused by the domain."""

import pytest

from flowgraph.parser.arguments import build_command_line

pytestmark = pytest.mark.edge

CRITERION = ["--given", "g", "--when", "w", "--then", "t"]
ADDS = {
    "story": ["add", "story", "a title", *CRITERION],
    "upkeep": ["add", "upkeep", "a title", *CRITERION],
    "bug": ["add", "bug", "a title", "--observed", "o", "--expected", "e"],
    "spike": ["add", "spike", "a title", "--hypothesis", "is it so?"],
}


def parsed(argv: list[str]) -> object:
    """The criterion realized of the arguments of the command line, parsed."""
    return build_command_line().parser.parse_args(argv).realizes


@pytest.mark.parametrize("kind", ADDS)
def test_an_add_of_each_kind_takes_the_criterion_as_typed(kind: str) -> None:
    assert parsed([*ADDS[kind], "--parent", "F-0001", "--realizes", "2"]) == "2"


@pytest.mark.parametrize("kind", ADDS)
def test_an_add_without_it_has_none(kind: str) -> None:
    assert parsed(ADDS[kind]) is None


def test_an_add_takes_a_word_that_is_no_number_for_the_domain_to_refuse() -> None:
    assert parsed([*ADDS["story"], "--realizes", "two"]) == "two"


def test_an_amend_takes_the_criterion_as_typed() -> None:
    assert parsed(["amend", "S-0001", "--realizes", "none"]) == "none"


def test_an_amend_without_it_has_none() -> None:
    assert parsed(["amend", "S-0001", "--title", "another"]) is None
