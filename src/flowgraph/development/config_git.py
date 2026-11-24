"""The git step that reads the configuration of a clone: the folder its record is named in.

fgraph never writes the key: the developer runs `git config fgraph.record <path>`. The worktrees
of a repository share the configuration of their clone, so each reads the folder under its own top.
"""

from pathlib import Path

from flowgraph.development.git import work_tree_of
from flowgraph.development.git_command import GitError, run_git
from flowgraph.record.location import KEY


def record_named(directory: Path) -> Path | None:
    """Adapter: the folder the key names under the top of the work tree the directory is inside.

    None outside a git work tree, with no key and for an empty value. Only the configuration of
    the clone is read: a key of the global configuration names nothing.
    """
    try:
        value = run_git(directory, "config", "--local", "--get", KEY)
    except GitError:
        return None
    top = work_tree_of(directory)
    if top is None or not value:
        return None
    return top / value
