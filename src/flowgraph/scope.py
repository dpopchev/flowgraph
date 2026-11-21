"""The scope of a branch: the work item it owns, and the store that saves that work item alone.

The branch `wi/<id>-<slug>` is the branch of the work item of that id. In a work tree on it
fgraph writes the file of that work item and no other file of the record; on any other branch
it leaves the Tasks of a started work item to the worktree of that work item.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import assert_never

from flowgraph.branch import MAIN
from flowgraph.commit import OpenGit
from flowgraph.item import ItemIdError, Store, parse_item_id, parse_work_item_id_of_any_kind
from flowgraph.queue import Queue
from flowgraph.task import TaskId
from flowgraph.work_item import (
    CompletedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemId,
    WorkItemIdError,
    WorkItemState,
    work_item_id_text,
)

# The name of the branch of a work item: `wi/`, its id, `-` and its slug.
OWNED = re.compile(r"wi/([A-Z]+-\d+)-.+")


@dataclass(frozen=True)
class Scope:
    """A branch a work item owns, and that work item."""

    branch: str
    owner: WorkItemId


# The scope of the branch a write is made on, or None when no work item owns that branch.
FindScope = Callable[[], Scope | None]

# The worktree the branch of that work item is checked out in, or None when it has none.
FindItemWorktree = Callable[[WorkItemId], Path | None]


class NotOnMainError(Exception):
    """A work item started in a work tree that is not on main; names where it starts."""


class OutOfScopeError(Exception):
    """A write on the branch of a work item to another file of the record; names the owner."""


def scope_of(branch: str) -> Scope | None:
    """The scope of the branch: None unless it is named `wi/<id>-<slug>` for a work item id."""
    named = OWNED.fullmatch(branch)
    if named is None:
        return None
    try:
        owner = parse_work_item_id_of_any_kind(named.group(1))
    except WorkItemIdError:
        return None
    return Scope(branch, owner)


def scope_in(record: Path, open_git: OpenGit) -> Scope | None:
    """The scope of the branch the work tree of the record is on; None outside a work tree."""
    work_tree = open_git(record)
    return None if work_tree is None else scope_of(work_tree.current_branch())


def _alone(scope: Scope) -> str:
    """What a refusal says of the scope: its branch and the one work item it writes."""
    return f"the branch {scope.branch} writes {work_item_id_text(scope.owner)} alone"


def worktree_of_item(record: Path, open_git: OpenGit, item_id: WorkItemId) -> Path | None:
    """The worktree a branch `wi/<id>-*` of the work item is checked out in; None without one.

    A record outside a git work tree has none.
    """
    work_tree = open_git(record)
    if work_tree is None:
        return None
    branches = work_tree.find_branches(f"wi/{work_item_id_text(item_id)}-*")
    found = [work_tree.find_worktree(branch) for branch in branches]
    return next((path for path in found if path is not None), None)


def _is_started(item: WorkItemState) -> bool:
    """True for a started work item."""
    match item:
        case StartedWorkItem():
            return True
        case WorkItem() | CompletedWorkItem():
            return False
        case _ as unreachable:
            assert_never(unreachable)


def within(store: Store, find_scope: FindScope, find_worktree: FindItemWorktree) -> Store:
    """The store that saves within the scope found when it saves; its reads are as they were.

    On the branch of a work item a save of another work item, or of the queue, raises
    OutOfScopeError and writes nothing. On any other branch so does a Task write of a started
    work item that has a worktree: the save of a started work item that was started already.
    The scope and the worktree are asked for only at a save.
    """

    def save_work_item(item: WorkItemState) -> None:
        scope = find_scope()
        named = work_item_id_text(item.id)
        if scope is not None and item.id != scope.owner:
            raise OutOfScopeError(f"{named} is not written here: {_alone(scope)}")
        if scope is None and _is_started(item) and _is_started(store.load_work_item(item.id)):
            worktree = find_worktree(item.id)
            if worktree is not None:
                raise OutOfScopeError(
                    f"{named} is started: its Tasks are written in its worktree, {worktree}"
                )
        store.save_work_item(item)

    def save_queue(queue: Queue) -> None:
        scope = find_scope()
        if scope is not None:
            raise OutOfScopeError(f"the Backlog is not reordered here: {_alone(scope)}")
        store.save_queue(queue)

    return replace(store, save_work_item=save_work_item, save_queue=save_queue)


def check_start_on_main(item: str, record: Path, open_git: OpenGit) -> None:
    """Check that the start of the item of that id is made where it may be.

    A work item starts on main alone: raises NotOnMainError naming the branch the work tree of
    the record is on and, when the repository has one, the work tree that is on main. A Task
    starts anywhere, a record outside a git work tree is not checked, and a text that is no id
    is left to the start, which refuses it.
    """
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    match item_id:
        case TaskId():
            return
        case WorkItemId():
            work_tree = open_git(record)
            on = MAIN if work_tree is None else work_tree.current_branch()
            if work_tree is None or on == MAIN:
                return
            home = work_tree.find_worktree(MAIN)
            where = MAIN if home is None else f"{MAIN}, in {home}"
            here = f"{work_tree.path} is on {on or 'no branch'}"
            raise NotOnMainError(f"{work_item_id_text(item_id)} starts on {where}: {here}")
        case _ as unreachable:
            assert_never(unreachable)
