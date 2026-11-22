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

from flowgraph.development.branch import MAIN
from flowgraph.development.commit import OpenGit, kept_in
from flowgraph.feature import FeatureState
from flowgraph.item import ItemIdError, parse_item_id, parse_work_item_id_of_any_kind
from flowgraph.parent import FeatureIdError, feature_id_text, parse_feature_id
from flowgraph.record import Settings
from flowgraph.record.queue import Queue
from flowgraph.record.store import Store
from flowgraph.task import TaskId
from flowgraph.term import Term
from flowgraph.work_item import (
    CompletedWorkItem,
    RemovedWorkItem,
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
    """The scope of the branch the work tree that keeps the record is on; None when none does."""
    work_tree = kept_in(record, open_git)
    return None if work_tree is None else scope_of(work_tree.current_branch())


def _alone(scope: Scope) -> str:
    """What a refusal says of the scope: its branch and the one work item it writes."""
    return f"the branch {scope.branch} writes {work_item_id_text(scope.owner)} alone"


def worktree_of_item(record: Path, open_git: OpenGit, item_id: WorkItemId) -> Path | None:
    """The worktree a branch `wi/<id>-*` of the work item is checked out in; None without one.

    A record outside a git work tree has none, and neither has a record git ignores.
    """
    work_tree = kept_in(record, open_git)
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
        case WorkItem() | CompletedWorkItem() | RemovedWorkItem():
            return False
        case _ as unreachable:
            assert_never(unreachable)


def within(store: Store, find_scope: FindScope, find_worktree: FindItemWorktree) -> Store:
    """The store that saves within the scope found when it saves; its reads are as they were.

    On the branch of a work item a save of another work item, of the queue, of a Feature, of a
    term or of the settings raises OutOfScopeError and writes nothing. On any other branch so
    does a Task write of a started work item that has a worktree: the save of a started work
    item that was started already. The scope and the worktree are asked for only at a save.
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

    def save_feature(feature: FeatureState) -> None:
        scope = find_scope()
        if scope is not None:
            named = feature_id_text(feature.id)
            raise OutOfScopeError(f"{named} is not written here: {_alone(scope)}")
        store.features.save_feature(feature)

    def save_term(term: Term) -> None:
        scope = find_scope()
        if scope is not None:
            raise OutOfScopeError(f"{term.name} is not added here: {_alone(scope)}")
        store.terms.save_term(term)

    def save_settings(settings: Settings) -> None:
        scope = find_scope()
        if scope is not None:
            raise OutOfScopeError(f"the configuration is not set here: {_alone(scope)}")
        store.save_settings(settings)

    features = replace(store.features, save_feature=save_feature)
    terms = replace(store.terms, save_term=save_term)
    return replace(
        store,
        save_work_item=save_work_item,
        save_queue=save_queue,
        features=features,
        terms=terms,
        save_settings=save_settings,
    )


def _started_on_main(item: str) -> str | None:
    """The id, as it is written, the text names when it starts on main alone; None otherwise.

    A work item and a Feature do; a Task does not, and neither does a text that is no id.
    """
    try:
        return feature_id_text(parse_feature_id(item))
    except FeatureIdError:
        pass
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return None
    match item_id:
        case TaskId():
            return None
        case WorkItemId():
            return work_item_id_text(item_id)
        case _ as unreachable:
            assert_never(unreachable)


def check_start_on_main(item: str, record: Path, open_git: OpenGit) -> None:
    """Check that the start of the item of that id is made where it may be.

    A work item starts on main alone, and so does a Feature, which starts its first work item:
    raises NotOnMainError naming the branch the work tree of the record is on and, when the
    repository has one, the work tree that is on main. A Task starts anywhere, a record outside
    a git work tree is not checked, and a text that is no id is left to the start, which refuses
    it. A record git ignores is checked as any other: its start makes a branch too.
    """
    _check_on_main(item, "starts", record, open_git)


def check_complete_on_main(item: str, record: Path, open_git: OpenGit) -> None:
    """Check that the completion of the item of that id is made where it may be.

    A work item completes on main alone, as it starts there: its landing completes it, and so
    the next work item of its Feature, which its completion starts, is started on main too. A
    Feature does, and a Task completes anywhere. Raises NotOnMainError as check_start_on_main
    does.
    """
    _check_on_main(item, "completes", record, open_git)


def _check_on_main(item: str, move: str, record: Path, open_git: OpenGit) -> None:
    """Check that the move of the item of that id is made on main when the item makes it there.

    Raises NotOnMainError naming the move, the branch the work tree is on and the work tree on
    main, when the repository has one.
    """
    named = _started_on_main(item)
    if named is None:
        return
    work_tree = open_git(record)
    on = MAIN if work_tree is None else work_tree.current_branch()
    if work_tree is None or on == MAIN:
        return
    home = work_tree.find_worktree(MAIN)
    where = MAIN if home is None else f"{MAIN}, in {home}"
    here = f"{work_tree.path} is on {on or 'no branch'}"
    raise NotOnMainError(f"{named} {move} on {where}: {here}")
