"""The command a call of a tool runs, and the refusal of arguments it does not take."""

from pathlib import Path

import pytest

from flowgraph.mcp.reads import STATUS
from flowgraph.mcp.tools import Command, ToolArgumentsError, command_of

pytestmark = pytest.mark.model

REFUSED = "the arguments of status are refused: "


def test_the_directory_and_the_argv_of_status() -> None:
    assert command_of(STATUS, {"directory": "/src/project"}) == Command(
        Path("/src/project"), ["status", "--format", "json"]
    )


def test_a_relative_directory_is_kept_as_given() -> None:
    assert command_of(STATUS, {"directory": "project"}).directory == Path("project")


def test_a_missing_directory_is_refused() -> None:
    with pytest.raises(ToolArgumentsError, match=f"^{REFUSED}directory: Field required$"):
        command_of(STATUS, {})


def test_a_directory_that_is_no_string_is_refused() -> None:
    message = f"^{REFUSED}directory: Input should be a valid string$"
    with pytest.raises(ToolArgumentsError, match=message):
        command_of(STATUS, {"directory": 3})


def test_an_argument_status_does_not_take_is_refused() -> None:
    message = f"^{REFUSED}more: Extra inputs are not permitted$"
    with pytest.raises(ToolArgumentsError, match=message):
        command_of(STATUS, {"directory": "/x", "more": 1})
