"""The reads of fgraph mcp: the tools that print a view of the record as JSON and write nothing."""

from flowgraph.mcp.tools import Tool, ToolArguments


def _status(_: ToolArguments) -> list[str]:
    return ["status", "--format", "json"]


STATUS = Tool(
    "status",
    "List the items of the record by bucket, as fgraph status --format json prints them; "
    "run in the worktree of a work item, the record of main",
    ToolArguments,
    _status,
)

READ_TOOLS = (STATUS,)
