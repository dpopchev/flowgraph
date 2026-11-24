"""The remove of a started work item: made on main, from the copy its worktree holds (S-0148).

A started or a blocked work item is removed on main, where it was started and where it would
complete. Its Tasks are written in its worktree, so it is removed whole from that copy and saved
in the record of main alone; the copy of the worktree is then stale, as after a landing.
"""

from pathlib import Path

from flowgraph.development.commit import OpenGit
from flowgraph.development.scope import check_on_main
from flowgraph.item.id import parse_work_item_id_of_any_kind
from flowgraph.record.store import Store
from flowgraph.work_item import IN_PROGRESS, WorkItemIdError, work_item_id_text


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
