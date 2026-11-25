"""The moves of fgraph mcp: the argv of the command each call runs, and the arguments refused."""

from typing import Any

import pytest

from flowgraph.mcp.moves import MOVE_TOOLS
from flowgraph.mcp.tools import Tool, ToolArgumentsError, command_of

pytestmark = pytest.mark.view

DIRECTORY = "/src/project"
KINDS = ["finding", "decision", "deviation", "progress"]


def tool(name: str) -> Tool[Any]:
    """The move of that name."""
    return next(each for each in MOVE_TOOLS if each.name == name)


def argv(name: str, **arguments: str) -> list[str]:
    """The argv a call of the move with those arguments runs, in DIRECTORY."""
    return command_of(tool(name), {"directory": DIRECTORY, **arguments}).argv


def test_the_moves_are_the_seven_commands_in_order() -> None:
    assert [each.name for each in MOVE_TOOLS] == [
        "start",
        "hand",
        "block",
        "unblock",
        "note",
        "commit",
        "complete",
    ]


def test_a_start_runs_start_of_the_id() -> None:
    assert argv("start", id="S-0001") == ["start", "S-0001"]


def test_a_start_with_an_agent_hands_it() -> None:
    assert argv("start", id="S-0001", agent="sonnet-a1") == [
        "start",
        "S-0001",
        "--agent=sonnet-a1",
    ]


def test_a_start_with_no_id_runs_start() -> None:
    assert argv("start") == ["start"]


def test_a_start_with_no_id_hands_it_to_the_agent() -> None:
    assert argv("start", agent="sonnet-a1") == ["start", "--agent=sonnet-a1"]


def test_a_start_requires_the_directory_alone() -> None:
    assert tool("start").arguments.model_json_schema()["required"] == ["directory"]


def test_a_hand_names_the_agent() -> None:
    assert argv("hand", id="S-0001", agent="opus-b2") == ["hand", "S-0001", "--agent=opus-b2"]


def test_a_hand_with_no_agent_is_refused() -> None:
    message = "^the arguments of hand are refused: agent: Field required$"
    with pytest.raises(ToolArgumentsError, match=message):
        argv("hand", id="S-0001")


def test_a_block_names_the_reason_and_what_it_waits_on() -> None:
    assert argv("block", id="T-0001", reason="r", waiting_on="w") == [
        "block",
        "T-0001",
        "--reason=r",
        "--waiting-on=w",
    ]


def test_an_unblock_runs_unblock_of_the_id() -> None:
    assert argv("unblock", id="T-0001") == ["unblock", "T-0001"]


@pytest.mark.parametrize("kind", KINDS)
def test_a_note_gives_its_text_as_the_option_of_its_kind(kind: str) -> None:
    assert argv("note", id="S-0001", kind=kind, text="a text") == [
        "note",
        "S-0001",
        f"--{kind}=a text",
    ]


def test_a_note_of_another_kind_is_refused() -> None:
    message = (
        "^the arguments of note are refused: kind: "
        "Input should be 'finding', 'decision', 'deviation' or 'progress'$"
    )
    with pytest.raises(ToolArgumentsError, match=message):
        argv("note", id="S-0001", kind="other", text="a text")


def test_a_text_that_starts_with_a_dash_is_kept_as_the_value() -> None:
    assert argv("note", id="S-0001", kind="finding", text="--x")[-1] == "--finding=--x"


def test_a_commit_runs_commit_of_the_id_with_its_message() -> None:
    assert argv("commit", id="T-0001", message="fix: a change") == [
        "commit",
        "T-0001",
        "--message=fix: a change",
    ]


def test_a_commit_with_no_message_is_refused() -> None:
    message = "^the arguments of commit are refused: message: Field required$"
    with pytest.raises(ToolArgumentsError, match=message):
        argv("commit", id="T-0001")


def test_a_commit_message_that_starts_with_a_dash_is_kept_as_the_value() -> None:
    assert argv("commit", id="T-0001", message="--x")[-1] == "--message=--x"


def test_a_complete_names_its_commit() -> None:
    assert argv("complete", id="T-0001", commit="3e9ae5c") == [
        "complete",
        "T-0001",
        "--commit=3e9ae5c",
    ]


def test_a_complete_with_no_commit_runs_complete_of_the_id() -> None:
    assert argv("complete", id="T-0001") == ["complete", "T-0001"]


def test_no_move_takes_an_approval() -> None:
    schemas = [each.arguments.model_json_schema()["properties"] for each in MOVE_TOOLS]
    assert [schema for schema in schemas if "approved" in schema] == []
