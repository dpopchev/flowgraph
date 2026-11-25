"""A tool as tools/list gives it: its name, its description and the schema of its arguments."""

import pytest

from flowgraph.mcp.reads import STATUS
from flowgraph.mcp.tools import tool_listed

pytestmark = pytest.mark.view


def test_the_listing_holds_a_description_a_schema_and_a_name() -> None:
    assert sorted(tool_listed(STATUS)) == ["description", "inputSchema", "name"]


def test_the_name_is_status() -> None:
    assert tool_listed(STATUS)["name"] == "status"


def test_the_description_is_that_of_the_tool() -> None:
    assert tool_listed(STATUS)["description"] == STATUS.description


def test_the_schema_is_of_an_object() -> None:
    assert tool_listed(STATUS)["inputSchema"]["type"] == "object"


def test_the_schema_requires_the_directory() -> None:
    assert tool_listed(STATUS)["inputSchema"]["required"] == ["directory"]


def test_the_schema_takes_no_other_argument() -> None:
    assert tool_listed(STATUS)["inputSchema"]["additionalProperties"] is False


def test_the_directory_is_a_string() -> None:
    assert tool_listed(STATUS)["inputSchema"]["properties"]["directory"]["type"] == "string"
