"""The git step of a landing through a pull request: the branch of the work item pushed."""

from pathlib import Path

from flowgraph.development.git import upstream_of
from flowgraph.development.git_command import run_git


def push_beside(work_tree: Path, branch: str, beside: str) -> str:
    """Adapter: push the branch, under its own name, to the remote the other branch tracks.

    Returns the name of that remote. Sets no upstream and writes no git config. Raises GitError
    when the other branch tracks none, and naming the command when git refuses the push.
    """
    remote, _ = upstream_of(work_tree, beside)
    run_git(work_tree, "push", "--quiet", remote, f"refs/heads/{branch}:refs/heads/{branch}")
    return remote
