"""A Bug: a behavior that fails, the kind of work item whose ids are written `B-0001`."""

from flowgraph.bug.model import (
    BUG,
    BugIdError,
    bug_id_text,
    make_bug,
    make_bug_id,
    next_bug_id,
    parse_bug_id,
)

__all__ = [
    "BUG",
    "BugIdError",
    "bug_id_text",
    "make_bug",
    "make_bug_id",
    "next_bug_id",
    "parse_bug_id",
]
