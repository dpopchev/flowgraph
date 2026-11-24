"""The start of a work item is refused before it writes while the branch it would make is there.

The start takes over no branch that is there (the decision of the developer of 2026-11-23): the
developer deletes the branch or gives another slug. Nothing is read unless the development is on.
"""

from pathlib import Path
from typing import assert_never

from flowgraph.development.branch import branch_of, make_slug, slug_of_title
from flowgraph.development.commit import OpenGit
from flowgraph.item.commands import ItemIdError, parse_item_id
from flowgraph.record import Config
from flowgraph.record.store import Store
from flowgraph.task import TaskId
from flowgraph.work_item import WorkItem, WorkItemId, work_item_id_text

# The refusal of a start whose branch is there, with what is named and the branch.
BRANCH_THERE = (
    "{named} cannot start: the branch {branch} is there already -- delete it or give another --slug"
)


class BranchExistsError(Exception):
    """A start whose branch is there already; names the branch."""


def check_branch_free(
    item: str, slug: str | None, store: Store, record: Path, open_git: OpenGit, config: Config
) -> None:
    """Check that the branch the start of the item would make is not there already.

    Raises BranchExistsError for a work item in Backlog that holds a Task while its branch is
    there, the slug the one given else the one of its title, and SlugError for a slug that is
    none. One with no Task and one past Backlog are left to the start, which refuses them in its
    own words, and so are a Task and a text that is no id. Nothing is read with the development
    off or outside a git work tree; a record git ignores is checked as any other.
    """
    if not config.development.enabled:
        return
    try:
        item_id = parse_item_id(item)
    except ItemIdError:
        return
    match item_id:
        case TaskId():
            return
        case WorkItemId():
            pass
        case _ as unreachable:
            assert_never(unreachable)
    work_tree = open_git(record)
    if work_tree is None:
        return
    held = store.load_work_item(item_id)
    match held:
        case WorkItem(tasks=()):
            return
        case WorkItem():
            pass
        case _:
            return
    slug_made = make_slug(slug) if slug is not None else slug_of_title(held.title)
    made = branch_of(item_id, slug_made, work_tree.path.resolve())
    if work_tree.find_branches(made.name):
        text = work_item_id_text(item_id)
        raise BranchExistsError(BRANCH_THERE.format(named=text, branch=made.name))
