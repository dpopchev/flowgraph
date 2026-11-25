"""The result of a call of a tool: what the run printed, or its refusal as a tool error."""

import pytest

from flowgraph.mcp.tools import Ran, ran_result, refused_result

pytestmark = pytest.mark.view

USAGE = "usage: fgraph status [-h]\n"
REFUSAL = "fgraph: error: no Story S-0009 in the record"


def test_an_output_is_one_text() -> None:
    assert ran_result(Ran(0, "{}\n", "")) == {"content": [{"type": "text", "text": "{}\n"}]}


def test_a_warning_at_exit_zero_is_a_second_text() -> None:
    assert ran_result(Ran(0, "{}\n", "warning: old\n"))["content"] == [
        {"type": "text", "text": "{}\n"},
        {"type": "text", "text": "warning: old\n"},
    ]


def test_a_refusal_is_its_last_line_as_a_tool_error() -> None:
    assert ran_result(Ran(2, "", f"{USAGE}{REFUSAL}\n")) == {
        "content": [{"type": "text", "text": REFUSAL}],
        "isError": True,
    }


def test_a_refusal_with_no_line_names_the_status() -> None:
    assert ran_result(Ran(2, "", ""))["content"] == [
        {"type": "text", "text": "fgraph exited with status 2"}
    ]


def test_a_refused_text_is_a_tool_error() -> None:
    assert refused_result("a line") == {
        "content": [{"type": "text", "text": "a line"}],
        "isError": True,
    }
