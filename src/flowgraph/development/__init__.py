"""The development of a work item: its branch, its commits, its scope, its gate and its landing.

The branch and the gate are named here. The commit, the landing, the parallel start, the scope
and the worktrees run on the items of a record, which name a branch through this package, so
each is imported from its own module: commit, land, parallel, scope and worktrees.
"""

from flowgraph.development.branch import (
    MAIN,
    GitError,
    Slug,
    SlugError,
    branch_of,
    check_slug_branched,
    make_slug,
    slug_of_title,
)
from flowgraph.development.gate import GateError, RunGate, check_gate, run_gate

__all__ = [
    "MAIN",
    "GateError",
    "GitError",
    "RunGate",
    "Slug",
    "SlugError",
    "branch_of",
    "check_gate",
    "check_slug_branched",
    "make_slug",
    "run_gate",
    "slug_of_title",
]
