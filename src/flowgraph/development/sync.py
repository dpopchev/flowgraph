"""fgraph sync: merge main into the branch of a started work item, run in its worktree.

The work item is the one the branch names, whatever its state: the record is not read and
nothing of it is written. The git steps are those of flowgraph.development.sync_git, called by
name on the work tree and proved against the real git.
"""

from pathlib import Path

from flowgraph.development.branch import MAIN
from flowgraph.development.commit import OpenGit, Said
from flowgraph.development.scope import scope_of
from flowgraph.development.sync_git import head_of, holds, merge_branch, uncommitted
from flowgraph.record import DEVELOPMENT_ENABLED, Config


class SyncError(Exception):
    """A sync refused: with the development off, outside a git work tree, off the branch of a
    work item, with a change not committed, or of a main that conflicts with the branch."""


def sync_branch(record: Path, open_git: OpenGit, config: Config) -> Said:
    """Merge main into the branch the work tree of the record is on; say what was done.

    The merge is one commit, never a fast-forward; a branch that holds main already is left as it
    is. Raises SyncError, nothing merged, with the development off, outside a git work tree, off
    the branch of a work item, with a tracked file changed and not committed, and when main
    conflicts with the branch: the merge is then aborted and the files are named.
    """
    if not config.development.enabled:
        raise SyncError(
            "fgraph sync merges main into the branch of a work item:"
            f" the development is off -- run fgraph config set {DEVELOPMENT_ENABLED} true"
        )
    work_tree = open_git(record)
    if work_tree is None:
        raise SyncError(f"fgraph sync merges main: {record} is not inside a git work tree")
    on = work_tree.current_branch()
    if scope_of(on) is None:
        raise SyncError(
            "fgraph sync runs on the branch of a work item, wi/<id>-<slug>:"
            f" {work_tree.path} is on {on or 'no branch'}"
        )
    path = work_tree.path
    changed = uncommitted(path)
    if changed:
        raise SyncError(
            "fgraph sync merges main into a work tree with nothing uncommitted:"
            f" {path} holds {', '.join(changed)} -- commit it first"
        )
    if holds(path, MAIN):
        return Said(f"{on} holds main already at {head_of(path)}\n")
    conflicts = merge_branch(path, MAIN, f"chore: merge main into {on}")
    if conflicts:
        raise SyncError(
            f"main does not merge into {on}: conflict in {', '.join(conflicts)}"
            " -- nothing is merged, the branch is as it was"
        )
    return Said(f"merged main into {on} at {head_of(path)}\n")
