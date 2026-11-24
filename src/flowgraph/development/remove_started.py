"""The remove of a started work item: made on main, from the copy its worktree holds (S-0148).

A started or a blocked work item is removed on main, where it was started and where it would
complete. Its Tasks are written in its worktree, so it is removed whole from that copy and saved
in the record of main alone; the copy of the worktree is then stale, as after a landing.

Once that write is committed, the worktree of each branch of the work item and the branch go
when main holds every commit of the branch, since nothing of it is lost then; otherwise both are
left, as the work on them is not on main, and said, for the developer to remove by hand. A
worktree holding a change is refused by git and left, and so is its branch.
"""

from dataclasses import replace
from pathlib import Path

from flowgraph.development.branch import MAIN
from flowgraph.development.commit import OpenGit, Said, WorkTree
from flowgraph.development.git import GitError
from flowgraph.development.scope import check_on_main
from flowgraph.item.commands import Written
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.record import Config
from flowgraph.record.store import Store
from flowgraph.work_item import IN_PROGRESS, WorkItemIdError, work_item_id_text

# The line of a branch left, and of a branch removed with its worktree and without one.
LEFT = "left branch {branch} in {path}: main does not hold every commit of it\n"
REMOVED = "removed branch {branch} in {path}\n"
REMOVED_ALONE = "removed branch {branch}\n"


def check_remove_on_main(item: str, store: Store, record: Path, open_git: OpenGit) -> None:
    """Check that the remove of a started or a blocked work item of that id is made on main.

    Raises NotOnMainError naming the branch the work tree of the record is on and the work tree
    on main. A work item in any other state, a Feature, a Task and a text that is no id are left
    to the remove, and so is a record outside a git work tree. It is checked with the
    development off too, as a complete is.
    """
    try:
        item_id = parse_work_item_id_of_any_kind(item)
    except WorkItemIdError:
        return
    named = work_item_id_text(item_id)
    rows = store.find_work_item_rows(item_id.kind)
    if any(row.id == named and row.state in IN_PROGRESS for row in rows):
        check_on_main(named, "is removed", record, open_git)


def _remove(work_tree: WorkTree, branch: str, path: Path | None) -> None:
    """Remove the worktree of the branch when it has one, then the branch; GitError if refused."""
    if path is not None:
        work_tree.landing.remove_worktree(path)
    work_tree.landing.delete_branch(branch)


def _unbranched(named: str, branch: str, work_tree: WorkTree, open_git: OpenGit) -> str:
    """Remove the worktree and the branch when main holds every commit of it; the line said.

    Raises GitError naming the branch kept when git refuses a step, after the write.
    """
    path = work_tree.find_worktree(branch)
    if path is not None:
        there = open_git(path)
        if there is None or not there.landing.can_fast_forward(MAIN):
            return LEFT.format(branch=branch, path=path)
    try:
        _remove(work_tree, branch, path)
    except GitError as error:
        raise GitError(f"{error} -- {named} is removed, its branch {branch} is not") from error
    if path is None:
        return REMOVED_ALONE.format(branch=branch)
    return REMOVED.format(branch=branch, path=path)


def branch_removed(
    written: Written, said: Said, record: Path, open_git: OpenGit, config: Config
) -> Said:
    """What the remove says once committed, with a line for each branch of the work item.

    The branch of a started work item removed goes with its worktree when main holds every
    commit of it; otherwise both are left and said. Nothing is asked of git for a work item
    removed from Backlog, with the development off and outside a git work tree.
    """
    if written.unbranches is None or not config.development.enabled:
        return said
    work_tree = open_git(record)
    if work_tree is None:
        return said
    named = work_item_id_text(written.unbranches)
    branches = work_tree.find_branches(f"wi/{named}-*")
    lines = [_unbranched(named, branch, work_tree, open_git) for branch in branches]
    return replace(said, out=said.out + "".join(lines))
