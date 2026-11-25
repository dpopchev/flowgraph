"""The reads of fgraph mcp: the tools that print a view of the record as JSON and write nothing."""

from pydantic import Field

from flowgraph.mcp.tools import Tool, ToolArguments


class BriefArguments(ToolArguments):
    """The arguments of brief: the id of a work item."""

    id: str = Field(description="the id of the work item, in any state, as S-0001")


class ShowArguments(ToolArguments):
    """The arguments of show: the id of a work item or of a Feature, or the name of a term."""

    id: str = Field(
        description="the id of a work item or of a Feature, as S-0001 or F-0001, "
        "or the name of a term"
    )


class AboutArguments(ToolArguments):
    """The arguments of about: the id of a work item or of a Feature, a term or a file."""

    id: str = Field(
        description="the id of a work item or of a Feature, the name of a term, "
        "or the path of a file from the directory"
    )


def _status(_: ToolArguments) -> list[str]:
    return ["status", "--format", "json"]


def _brief(arguments: BriefArguments) -> list[str]:
    return ["brief", arguments.id, "--format", "json"]


def _show(arguments: ShowArguments) -> list[str]:
    return ["show", arguments.id, "--format", "json"]


def _knowledge(_: ToolArguments) -> list[str]:
    return ["knowledge", "--format", "json"]


def _about(arguments: AboutArguments) -> list[str]:
    return ["about", arguments.id, "--format", "json"]


STATUS = Tool(
    "status",
    "List the items of the record by bucket, as fgraph status --format json prints them; "
    "run in the worktree of a work item, the record of main",
    ToolArguments,
    _status,
)

BRIEF = Tool(
    "brief",
    "Print the brief of a work item, as fgraph brief ID --format json prints it",
    BriefArguments,
    _brief,
)

SHOW = Tool(
    "show",
    "Print a work item, a Feature or a term, as fgraph show ID --format json prints it",
    ShowArguments,
    _show,
)

KNOWLEDGE = Tool(
    "knowledge",
    "List the knowledge lines of the record, as fgraph knowledge --format json prints them",
    ToolArguments,
    _knowledge,
)

ABOUT = Tool(
    "about",
    "List the links of a work item, a Feature, a term or a file, "
    "as fgraph about ID --format json prints them",
    AboutArguments,
    _about,
)

READ_TOOLS = (STATUS, BRIEF, SHOW, KNOWLEDGE, ABOUT)
