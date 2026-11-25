"""The closing of fgraph mcp: the argv of the command each call runs, and the arguments refused."""

from typing import Any

import pytest

from flowgraph.mcp.closing import CLOSING_TOOLS
from flowgraph.mcp.tools import Tool, ToolArgumentsError, command_of

pytestmark = pytest.mark.view

DIRECTORY = "/src/project"


def tool(name: str) -> Tool[Any]:
    """The closing tool of that name."""
    return next(each for each in CLOSING_TOOLS if each.name == name)


def argv(name: str, **arguments: Any) -> list[str]:
    """The argv a call of the tool with those arguments runs, in DIRECTORY."""
    return command_of(tool(name), {"directory": DIRECTORY, **arguments}).argv


def test_the_closing_tools_are_land_and_verify() -> None:
    assert [each.name for each in CLOSING_TOOLS] == ["land", "verify"]


def test_a_land_runs_land_of_the_id() -> None:
    assert argv("land", id="S-0001") == ["land", "S-0001"]


def test_a_land_with_a_message_gives_it() -> None:
    assert argv("land", id="S-0001", message="feat: land S-0001") == [
        "land",
        "S-0001",
        "--message=feat: land S-0001",
    ]


def test_a_land_given_the_approval_is_refused() -> None:
    message = "^the arguments of land are refused: approved: Extra inputs are not permitted$"
    with pytest.raises(ToolArgumentsError, match=message):
        argv("land", id="S-0001", approved=True)


@pytest.mark.parametrize("answer", ["yes", "no"])
def test_a_verify_gives_its_text_as_the_option_of_its_answer(answer: str) -> None:
    assert argv("verify", id="S-0001", answer=answer, text="it holds") == [
        "verify",
        "S-0001",
        f"--{answer}=it holds",
    ]


def test_a_verify_of_another_answer_is_refused() -> None:
    message = "^the arguments of verify are refused: answer: Input should be 'yes' or 'no'$"
    with pytest.raises(ToolArgumentsError, match=message):
        argv("verify", id="S-0001", answer="maybe", text="it holds")
