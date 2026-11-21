"""An item of any kind, named by its id: the store of a record, and the commands by id.

Each command reads the id, finds the kind it names and runs the work item command on the store;
it returns the line fgraph writes, or raises the refusal of the move.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import assert_never

from flowgraph import branch, work_item
from flowgraph.branch import GitError, SlugError, branch_of, make_slug, slug_of_title
from flowgraph.criterion import make_commit
from flowgraph.queue import LoadQueue, SaveQueue, queued, read_queue, reorder, write_queue
from flowgraph.record import ITEMS, Now
from flowgraph.story import STORY
from flowgraph.task import TaskId, TaskIdError, parse_task_id, task_id_text
from flowgraph.text import show_text, status_text
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import (
    FindTaskIds,
    Kind,
    LoadWorkItem,
    SaveWorkItem,
    WorkItemDetail,
    WorkItemId,
    WorkItemIdError,
    WorkItemRow,
    parse_work_item_id,
    work_item_id_text,
)

# The kinds of work item a record holds, in the order fgraph reads them.
KINDS: tuple[Kind, ...] = (STORY, UPKEEP)

# The state of a row in Backlog, as the record writes it.
BACKLOG = "backlog"

# The rows of the work items of that kind in the record; an empty list when it holds none.
FindKindRows = Callable[[Kind], list[WorkItemRow]]

# The work item of that id as plain data; raises WorkItemNotFoundError when the record holds none.
FindWorkItemDetail = Callable[[WorkItemId], WorkItemDetail]

# The id of an item of any kind.
ItemId = WorkItemId | TaskId

# The path of the file of the work item of that id, whether or not it exists.
FindWorkItemFile = Callable[[WorkItemId], Path]

# The message of the commit that holds the start of a work item, for its id.
START_MESSAGE = "chore: start {} in the record"


@dataclass(frozen=True)
class Store:
    """The reads and writes of one record, each already bound to its directory."""

    find_work_item_rows: FindKindRows
    load_work_item: LoadWorkItem
    find_work_item_detail: FindWorkItemDetail
    find_task_ids: FindTaskIds
    save_work_item: SaveWorkItem
    load_queue: LoadQueue
    save_queue: SaveQueue
    find_work_item_file: FindWorkItemFile


# The store of the record in that directory.
OpenStore = Callable[[Path], Store]


@dataclass(frozen=True)
class WorkTree:
    """The git work tree a record is inside: its top and its steps, each bound to it.

    `commit_file` commits one file, relative to the top, with a message and returns its sha;
    `add_worktree` checks out a new branch at a commit in a new worktree at a path. Each raises
    GitError when git refuses it.
    """

    path: Path
    commit_file: Callable[[Path, str], str]
    add_worktree: Callable[[str, Path, str], None]


# The git work tree the directory is inside, or None when it is inside none.
OpenGit = Callable[[Path], WorkTree | None]


@dataclass(frozen=True)
class Begun:
    """What a start says: its lines on the output and a warning on the error output, or none."""

    out: str
    warning: str = ""


class ItemIdError(ValueError):
    """A text that is the id of no kind of item."""


def read_every_task_id(record: Path) -> list[str]:
    """Adapter: the ids of every Task of every kind in the record, as written, in no order."""
    return [task for kind in KINDS for task in work_item.read_task_ids(record, kind)]


def work_item_file(record: Path, item_id: WorkItemId) -> Path:
    """The path of the file of the work item of that id in the record."""
    return record / ITEMS / f"{work_item_id_text(item_id)}.toml"


def open_files(record: Path) -> Store:
    """The store of the record in that directory, kept as its files."""
    return Store(
        find_work_item_rows=partial(work_item.read_work_item_rows, record),
        load_work_item=partial(work_item.read_work_item, record),
        find_work_item_detail=partial(work_item.read_work_item_detail, record),
        find_task_ids=partial(read_every_task_id, record),
        save_work_item=partial(work_item.write_work_item, record),
        load_queue=partial(read_queue, record, KINDS),
        save_queue=partial(write_queue, record, KINDS),
        find_work_item_file=partial(work_item_file, record),
    )


def open_git(directory: Path) -> WorkTree | None:
    """The git work tree the directory is inside, its steps run by git; None when in none."""
    top = branch.work_tree_of(directory)
    if top is None:
        return None
    return WorkTree(top, partial(branch.commit_file, top), partial(branch.add_worktree, top))


def kind_named(name: str) -> Kind:
    """The kind whose noun, in lower case, is the name; raises KeyError when none is."""
    named = {kind.noun.lower(): kind for kind in KINDS}
    return named[name]


def parse_work_item_id_of_any_kind(text: str) -> WorkItemId:
    """The id of a work item of any kind written as the text.

    Raises WorkItemIdError as the first kind does when the text is the id of none of them.
    """
    first, *others = KINDS
    for kind in others:
        try:
            return parse_work_item_id(kind, text)
        except WorkItemIdError:
            continue
    return parse_work_item_id(first, text)


def parse_item_id(text: str) -> ItemId:
    """The id of a work item of any kind, or of a Task, written as the text.

    Raises ItemIdError when the text is none of them.
    """
    parsers: list[Callable[[str], ItemId]] = [
        *(partial(parse_work_item_id, kind) for kind in KINDS),
        parse_task_id,
    ]
    for parse in parsers:
        try:
            return parse(text)
        except WorkItemIdError, TaskIdError:
            continue
    nouns = ", ".join(kind.noun for kind in KINDS)
    raise ItemIdError(f"{text!r} is no {nouns} or Task id")


def _rows_by_id(store: Store) -> dict[WorkItemId, WorkItemRow]:
    """The row of every work item in the record under its id, by kind and then by number."""
    return {
        parse_work_item_id(kind, row.id): row
        for kind in KINDS
        for row in store.find_work_item_rows(kind)
    }


def _backlog_as_added(rows: Mapping[WorkItemId, WorkItemRow]) -> list[WorkItemId]:
    """The work items in Backlog in the order added; those added at one time as the rows list."""
    backlog = [item_id for item_id, row in rows.items() if row.state == BACKLOG]
    return sorted(backlog, key=lambda item_id: rows[item_id].created)


def status_item(store: Store) -> str:
    """The text of the work items of every kind in the record, by bucket.

    The Backlog is listed in the order of its queue; the other buckets by kind and number.
    """
    rows = _rows_by_id(store)
    backlog = queued(store.load_queue(), _backlog_as_added(rows))
    moved_on = [row for row in rows.values() if row.state != BACKLOG]
    return status_text([*(rows[item_id] for item_id in backlog), *moved_on])


def reorder_item(item: str, before: str, store: Store) -> str:
    """Put the work item right before the other in the queue of the Backlog; the line saying so.

    Raises WorkItemIdError when a text is the id of no kind, NotInBacklogError when one of the
    two is not in Backlog and SameItemError when they are one work item; nothing is saved.
    """
    moved = parse_work_item_id_of_any_kind(item)
    other = parse_work_item_id_of_any_kind(before)
    reorder(
        item=moved,
        before=other,
        find_backlog=lambda: _backlog_as_added(_rows_by_id(store)),
        load_queue=store.load_queue,
        save_queue=store.save_queue,
    )
    return f"moved {work_item_id_text(moved)} before {work_item_id_text(other)}\n"


def show_item(item: str, store: Store) -> str:
    """The text of the work item of that id.

    Raises WorkItemIdError when the text is the id of no kind and WorkItemNotFoundError when the
    record holds no such item.
    """
    return show_text(store.find_work_item_detail(parse_work_item_id_of_any_kind(item)))


def add_item(
    kind: Kind,
    title: str,
    criterion: tuple[str, str, str],
    description: str,
    store: Store,
    now: Now,
) -> str:
    """Add a work item of that kind with its Given / When / Then; the line that says so.

    Raises EmptyPartError when the title or a part of the criterion is blank; nothing is saved.
    """
    given, when, then = criterion
    added = work_item.add_work_item(
        kind=kind,
        title=title,
        given=given,
        when=when,
        then=then,
        description=description,
        find_work_item_rows=partial(store.find_work_item_rows, kind),
        save_work_item=store.save_work_item,
        now=now,
    )
    return f"added {work_item_id_text(added)}\n"


def amend_item(item: str, parts: work_item.Amendment, store: Store) -> str:
    """Rewrite the parts named of the work item in Backlog of that id; the line that says so.

    Raises WorkItemIdError when the text is the id of no kind, or the refusal of the amend.
    """
    item_id = parse_work_item_id_of_any_kind(item)
    load, save = store.load_work_item, store.save_work_item
    work_item.amend_work_item(
        item_id=item_id, amendment=parts, load_work_item=load, save_work_item=save
    )
    return f"amended {work_item_id_text(item_id)}\n"


def write_task(
    parent: str, title: str, expected_output: str, description: str, store: Store, now: Now
) -> str:
    """Write a Task for the work item named as parent; the line that says so.

    Its id is the next free one across every kind. Raises WorkItemIdError when the parent is the
    id of no kind, WorkItemNotFoundError when the record holds no such item,
    CompletedAlreadyError when it is completed and EmptyPartError when a part is blank; nothing
    is saved.
    """
    written = work_item.add_task(
        parent=parse_work_item_id_of_any_kind(parent),
        title=title,
        expected_output=expected_output,
        description=description,
        load_work_item=store.load_work_item,
        find_task_ids=store.find_task_ids,
        save_work_item=store.save_work_item,
        now=now,
    )
    return f"added {task_id_text(written)} to {parent}\n"


def _load_holder(store: Store) -> work_item.LoadHolder:
    """The load of the work item that holds a Task, among the items of every kind."""

    def holder(task_id: TaskId) -> work_item.WorkItemState:
        ids = [
            parse_work_item_id(kind, row.id)
            for kind in KINDS
            for row in store.find_work_item_rows(kind)
        ]
        return work_item.holder_of(task_id, ids, store.load_work_item)

    return holder


def _start_work_item(
    item_id: WorkItemId, slug: str | None, store: Store, now: Now, record: Path, open_git: OpenGit
) -> Begun:
    """Start the work item, commit its file and check out its branch in a new worktree.

    Outside a git work tree it is started alone, with a warning. When the commit fails the file
    is put back as it was; when the worktree fails the start stays committed. Either raises
    GitError naming the git command.
    """
    previous = store.load_work_item(item_id)
    named = make_slug(slug) if slug is not None else slug_of_title(previous.title)
    work_tree = open_git(record)
    work_item.start_work_item(
        item_id=item_id,
        load_work_item=store.load_work_item,
        save_work_item=store.save_work_item,
        now=now,
    )
    started = f"started {work_item_id_text(item_id)}\n"
    if work_tree is None:
        warning = f"fgraph: warning: no branch made: {record} is not inside a git work tree\n"
        return Begun(started, warning)
    top = work_tree.path.resolve()
    file = store.find_work_item_file(item_id).resolve().relative_to(top)
    try:
        sha = work_tree.commit_file(file, START_MESSAGE.format(work_item_id_text(item_id)))
    except GitError:
        store.save_work_item(previous)
        raise
    made = branch_of(item_id, named, top)
    try:
        work_tree.add_worktree(made.name, made.path, sha)
    except GitError as error:
        raise GitError(
            f"{error} -- {work_item_id_text(item_id)} is started at {sha[:7]}, its branch is not"
        ) from error
    return Begun(f"{started}branch {made.name} in {made.path}\n")


def start_item(
    item: str, slug: str | None, store: Store, now: Now, *, record: Path, open_git: OpenGit
) -> Begun:
    """Start the work item or the Task of that id; what the start says.

    A work item is committed and branched when the record is inside a git work tree; its slug
    is the one given, else the slug of its title. Raises ItemIdError when the text is no id,
    SlugError when the slug is none or is given for a Task, the refusal of the start before
    anything is saved, or GitError when git refuses a step.
    """
    match parse_item_id(item):
        case WorkItemId() as item_id:
            return _start_work_item(item_id, slug, store, now, record, open_git)
        case TaskId() as task_id:
            if slug is not None:
                raise SlugError(f"--slug names the branch of a work item: {item} is a Task")
            holder = work_item.start_task(
                task_id=task_id,
                load_holder=_load_holder(store),
                save_work_item=store.save_work_item,
                now=now,
            )
            return Begun(f"started {task_id_text(task_id)} of {work_item_id_text(holder)}\n")
        case _ as unreachable:
            assert_never(unreachable)


def complete_item(item: str, sha: str, store: Store, now: Now) -> str:
    """Complete the work item or the Task of that id in that commit; the line that says so.

    Raises ItemIdError when the text is no id, CommitError when the sha is no commit, or the
    refusal of the complete; nothing is saved.
    """
    match parse_item_id(item):
        case WorkItemId() as item_id:
            commit = make_commit(sha)
            work_item.complete_work_item(
                item_id=item_id,
                commit=commit,
                load_work_item=store.load_work_item,
                save_work_item=store.save_work_item,
                now=now,
            )
            return f"completed {work_item_id_text(item_id)} at {commit.sha}\n"
        case TaskId() as task_id:
            commit = make_commit(sha)
            holder = work_item.complete_task(
                task_id=task_id,
                commit=commit,
                load_holder=_load_holder(store),
                save_work_item=store.save_work_item,
                now=now,
            )
            task = task_id_text(task_id)
            return f"completed {task} of {work_item_id_text(holder)} at {commit.sha}\n"
        case _ as unreachable:
            assert_never(unreachable)
