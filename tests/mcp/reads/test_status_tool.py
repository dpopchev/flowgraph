"""The tools of fgraph mcp that read the record."""

import pytest

from flowgraph.mcp.reads import READ_TOOLS, STATUS

pytestmark = pytest.mark.view


def test_the_tool_of_the_status_is_named_status() -> None:
    assert STATUS.name == "status"


def test_the_reads_are_the_five_tools_in_order() -> None:
    assert [tool.name for tool in READ_TOOLS] == ["status", "brief", "show", "knowledge", "about"]
