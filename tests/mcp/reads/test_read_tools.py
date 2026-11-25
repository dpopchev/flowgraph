"""The read tools of fgraph mcp: the command each runs, and the arguments refused."""

from pathlib import Path

import pytest

from flowgraph.mcp.reads import ABOUT, BRIEF, KNOWLEDGE, SHOW
from flowgraph.mcp.tools import Command, Tool, ToolArgumentsError, command_of

pytestmark = pytest.mark.view

DIRECTORY = Path("/src/project")


@pytest.mark.parametrize(("tool", "name"), [(BRIEF, "brief"), (SHOW, "show"), (ABOUT, "about")])
def test_the_command_of_a_tool_taking_an_id_is_its_command_with_json(tool: Tool, name: str) -> None:
    command = command_of(tool, {"directory": str(DIRECTORY), "id": "S-0001"})
    assert command == Command(DIRECTORY, [name, "S-0001", "--format", "json"])


def test_the_command_of_knowledge_takes_no_filter() -> None:
    assert command_of(KNOWLEDGE, {"directory": str(DIRECTORY)}) == Command(
        DIRECTORY, ["knowledge", "--format", "json"]
    )


def test_knowledge_given_an_id_is_refused() -> None:
    message = "^the arguments of knowledge are refused: id: Extra inputs are not permitted$"
    with pytest.raises(ToolArgumentsError, match=message):
        command_of(KNOWLEDGE, {"directory": str(DIRECTORY), "id": "S-0001"})


def test_brief_given_no_id_is_refused() -> None:
    message = "^the arguments of brief are refused: id: Field required$"
    with pytest.raises(ToolArgumentsError, match=message):
        command_of(BRIEF, {"directory": str(DIRECTORY)})


def test_the_command_of_show_of_a_term_takes_its_name() -> None:
    assert command_of(SHOW, {"directory": str(DIRECTORY), "id": "gate"}).argv == [
        "show",
        "gate",
        "--format",
        "json",
    ]
