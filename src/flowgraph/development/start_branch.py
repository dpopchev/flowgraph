"""The start of a work item or a Feature is refused before it writes while its branch is there.

A work item makes the branch of its own; a Feature, the branch of its first work item in Backlog.
The start takes over no branch that is there (the decision of the developer of 2026-11-23): the
developer deletes the branch or gives another slug. A start on the trunk makes no branch, so none
refuses it: nothing is read unless the development is on and its mode is branch.
"""

from pathlib import Path
from typing import assert_never

from flowgraph.development.branch import branch_of, make_slug, slug_of_title
from flowgraph.development.commit import OpenGit, WorkTree
from flowgraph.feature import (
    BlockedFeature,
    CompletedFeature,
    Feature,
    RemovedFeature,
    StartedFeature,
)
from flowgraph.feature.start import first_in_backlog
from flowgraph.item.commands import ItemIdError, parse_item_id
from flowgraph.parent import FeatureIdError, feature_id_text, parse_feature_id
from flowgraph.record import Config, branched
from flowgraph.record.store import Store
from flowgraph.task import TaskId
from flowgraph.work_item import (
    BlockedWorkItem,
    CompletedWorkItem,
    RemovedWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemId,
    WorkItemState,
    work_item_id_text,
)

# The refusal of a start whose branch is there, with what is named and the branch.
BRANCH_THERE = (
    "{named} cannot start: the branch {branch} is there already -- delete it or give another --slug"
)


class BranchExistsError(Exception):
    """A start whose branch is there already; names the branch."""


def _check_free(
    named: str, item_id: WorkItemId, title: str, slug: str | None, work_tree: WorkTree
) -> None:
    """Raise BranchExistsError naming what is started when the branch of the work item is there."""
    made_slug = make_slug(slug) if slug is not None else slug_of_title(title)
    made = branch_of(item_id, made_slug, work_tree.path.resolve())
    if work_tree.find_branches(made.name):
        raise BranchExistsError(BRANCH_THERE.format(named=named, branch=made.name))


def _with_task(held: WorkItemState) -> WorkItem | None:
    """The work item when it is in Backlog and holds a Task; None for one the start refuses."""
    match held:
        case WorkItem(tasks=()):
            return None
        case WorkItem():
            return held
        case StartedWorkItem() | BlockedWorkItem() | CompletedWorkItem() | RemovedWorkItem():
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _check_feature(
    feature: str, slug: str | None, store: Store, record: Path, open_git: OpenGit
) -> None:
    """Check the branch of the first work item a Feature starts, when it is in Backlog."""
    feature_id = parse_feature_id(feature)
    work_tree = open_git(record)
    if work_tree is None:
        return
    match store.features.load_feature(feature_id):
        case Feature():
            pass
        case StartedFeature() | BlockedFeature() | CompletedFeature() | RemovedFeature():
            return
        case _ as unreachable:
            assert_never(unreachable)
    first = first_in_backlog(feature_id, store)
    if first is None:
        return
    held = _with_task(store.load_work_item(first))
    if held is not None:
        _check_free(feature_id_text(feature_id), first, held.title, slug, work_tree)


def _check_work_item(
    item_id: WorkItemId, slug: str | None, store: Store, record: Path, open_git: OpenGit
) -> None:
    """Check the branch of a work item in Backlog that holds a Task."""
    work_tree = open_git(record)
    if work_tree is None:
        return
    held = _with_task(store.load_work_item(item_id))
    if held is not None:
        _check_free(work_item_id_text(item_id), item_id, held.title, slug, work_tree)


def check_branch_free(
    item: str, slug: str | None, store: Store, record: Path, open_git: OpenGit, config: Config
) -> None:
    """Check that the branch the start of the item would make is not there already.

    Raises BranchExistsError for a work item in Backlog that holds a Task while its branch is
    there, and for a Feature in Backlog while the branch of its first work item in Backlog is
    there, that one holding a Task; the slug is the one given, else the one of the title. Raises
    SlugError for a slug that is none and FeatureNotFoundError for a Feature the record does not
    hold. A work item with no Task and one past Backlog, a Feature past Backlog or with no work
    item in Backlog, a Task and a text that is no id are left to the start, which refuses them
    in its own words. Nothing is read with the development off or outside a git work tree; a
    record git ignores is checked as any other.
    """
    if not branched(config.development):
        return
    try:
        parse_feature_id(item)
    except FeatureIdError:
        pass
    else:
        _check_feature(item, slug, store, record, open_git)
        return
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    match item_id:
        case TaskId():
            return
        case WorkItemId():
            _check_work_item(item_id, slug, store, record, open_git)
        case _ as unreachable:
            assert_never(unreachable)
