"""A work item of any kind, named by its id: the store of a record, and the commands by id.

Each command reads the id, finds the kind it names and runs that kind's command on the store;
it returns the line fgraph writes, or raises the refusal of the move.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import assert_never

from flowgraph import story, upkeep
from flowgraph.criterion import make_commit
from flowgraph.record import Now
from flowgraph.story import (
    FindStoryRows,
    LoadStory,
    SaveStory,
    StoryDetail,
    StoryId,
    StoryIdError,
    parse_story_id,
    story_id_text,
)
from flowgraph.task import TaskId, TaskIdError, TaskNotFoundError, parse_task_id, task_id_text
from flowgraph.text import show_text
from flowgraph.upkeep import (
    FindUpkeepRows,
    LoadUpkeep,
    SaveUpkeep,
    UpkeepDetail,
    UpkeepId,
    UpkeepIdError,
    parse_upkeep_id,
    upkeep_id_text,
)

# The ids of every Task of one kind in the record, as written; an empty list when it holds none.
FindTaskIds = Callable[[], list[str]]

# The Story of that id as plain data; raises StoryNotFoundError when the record holds none.
FindStoryDetail = Callable[[StoryId], StoryDetail]

# The Upkeep of that id as plain data; raises UpkeepNotFoundError when the record holds none.
FindUpkeepDetail = Callable[[UpkeepId], UpkeepDetail]

# The id of an item of any kind.
ItemId = StoryId | UpkeepId | TaskId


@dataclass(frozen=True)
class Store:
    """The reads and writes of one record, each already bound to its directory."""

    find_story_rows: FindStoryRows
    load_story: LoadStory
    find_story_detail: FindStoryDetail
    find_task_ids: FindTaskIds
    save_story: SaveStory
    find_upkeep_rows: FindUpkeepRows
    load_upkeep: LoadUpkeep
    find_upkeep_detail: FindUpkeepDetail
    find_upkeep_task_ids: FindTaskIds
    save_upkeep: SaveUpkeep


# The store of the record in that directory.
OpenStore = Callable[[Path], Store]


class ItemIdError(ValueError):
    """A text that is the id of no kind of item."""


def open_files(record: Path) -> Store:
    """The store of the record in that directory, kept as its files."""
    return Store(
        find_story_rows=partial(story.read_story_rows, record),
        load_story=partial(story.read_story, record),
        find_story_detail=partial(story.read_story_detail, record),
        find_task_ids=partial(story.read_task_ids, record),
        save_story=partial(story.write_story, record),
        find_upkeep_rows=partial(upkeep.read_upkeep_rows, record),
        load_upkeep=partial(upkeep.read_upkeep, record),
        find_upkeep_detail=partial(upkeep.read_upkeep_detail, record),
        find_upkeep_task_ids=partial(upkeep.read_task_ids, record),
        save_upkeep=partial(upkeep.write_upkeep, record),
    )


def parse_item_id(text: str) -> ItemId:
    """The Story id, Upkeep id or Task id written as the text.

    Raises ItemIdError when the text is none of them.
    """
    parsers: list[tuple[Callable[[str], ItemId], type[ValueError]]] = [
        (parse_story_id, StoryIdError),
        (parse_upkeep_id, UpkeepIdError),
        (parse_task_id, TaskIdError),
    ]
    for parse, refused in parsers:
        try:
            return parse(text)
        except refused:
            continue
    raise ItemIdError(f"{text!r} is no Story, Upkeep or Task id")


def show_item(item: str, store: Store) -> str:
    """The text of the Story or the Upkeep of that id.

    Raises StoryIdError when the text is neither id, naming it as no Story id, and
    StoryNotFoundError or UpkeepNotFoundError when the record holds no such item.
    """
    try:
        upkeep_id = parse_upkeep_id(item)
    except UpkeepIdError:
        return show_text(store.find_story_detail(parse_story_id(item)))
    return show_text(store.find_upkeep_detail(upkeep_id))


def write_task(
    parent: str, title: str, expected_output: str, description: str, store: Store, now: Now
) -> str:
    """Write a Task for the Story or the Upkeep named as parent; the line that says so.

    Its id is the next free one across every kind. Raises StoryIdError when the parent is neither
    id, naming it as no Story id, StoryNotFoundError or UpkeepNotFoundError when the record holds
    no such parent, CompletedAlreadyError when it is completed and EmptyPartError when a part is
    blank; nothing is saved.
    """

    def taken() -> list[str]:
        return [*store.find_task_ids(), *store.find_upkeep_task_ids()]

    try:
        parse_upkeep_id(parent)
    except UpkeepIdError:
        written = story.add_task(
            parent=parent,
            title=title,
            expected_output=expected_output,
            description=description,
            load_story=store.load_story,
            find_task_ids=taken,
            save_story=store.save_story,
            now=now,
        )
        return f"added {task_id_text(written)} to {parent}\n"
    written = upkeep.add_task(
        parent=parent,
        title=title,
        expected_output=expected_output,
        description=description,
        load_upkeep=store.load_upkeep,
        find_task_ids=taken,
        save_upkeep=store.save_upkeep,
        now=now,
    )
    return f"added {task_id_text(written)} to {parent}\n"


def _start_task(task_id: TaskId, store: Store, now: Now) -> str:
    """Start the Task of that id in the Story or the Upkeep that holds it; the line that says so."""
    task = task_id_text(task_id)
    try:
        holder = story.start_task(
            task_id=task_id,
            find_story_rows=store.find_story_rows,
            load_story=store.load_story,
            save_story=store.save_story,
            now=now,
        )
    except TaskNotFoundError:
        kept = upkeep.start_task(
            task_id=task_id,
            find_upkeep_rows=store.find_upkeep_rows,
            load_upkeep=store.load_upkeep,
            save_upkeep=store.save_upkeep,
            now=now,
        )
        return f"started {task} of {upkeep_id_text(kept)}\n"
    return f"started {task} of {story_id_text(holder)}\n"


def start_item(item: str, store: Store, now: Now) -> str:
    """Start the Story, the Upkeep or the Task of that id; the line that says so.

    Raises ItemIdError when the text is no id, or the refusal of the start; nothing is saved.
    """
    match parse_item_id(item):
        case StoryId() as story_id:
            story.start_story(
                story_id=story_id,
                load_story=store.load_story,
                save_story=store.save_story,
                now=now,
            )
            return f"started {story_id_text(story_id)}\n"
        case UpkeepId() as upkeep_id:
            upkeep.start_upkeep(
                upkeep_id=upkeep_id,
                load_upkeep=store.load_upkeep,
                save_upkeep=store.save_upkeep,
                now=now,
            )
            return f"started {upkeep_id_text(upkeep_id)}\n"
        case TaskId() as task_id:
            return _start_task(task_id, store, now)
        case _ as unreachable:
            assert_never(unreachable)


def _complete_task(task_id: TaskId, sha: str, store: Store, now: Now) -> str:
    """Complete the Task of that id in the commit of that sha; the line that says so."""
    commit = make_commit(sha)
    task = task_id_text(task_id)
    try:
        holder = story.complete_task(
            task_id=task_id,
            commit=commit,
            find_story_rows=store.find_story_rows,
            load_story=store.load_story,
            save_story=store.save_story,
            now=now,
        )
    except TaskNotFoundError:
        kept = upkeep.complete_task(
            task_id=task_id,
            commit=commit,
            find_upkeep_rows=store.find_upkeep_rows,
            load_upkeep=store.load_upkeep,
            save_upkeep=store.save_upkeep,
            now=now,
        )
        return f"completed {task} of {upkeep_id_text(kept)} at {commit.sha}\n"
    return f"completed {task} of {story_id_text(holder)} at {commit.sha}\n"


def complete_item(item: str, sha: str, store: Store, now: Now) -> str:
    """Complete the Story, the Upkeep or the Task of that id in that commit; the line that says so.

    Raises ItemIdError when the text is no id, CommitError when the sha is no commit, or the
    refusal of the complete; nothing is saved.
    """
    match parse_item_id(item):
        case StoryId() as story_id:
            commit = make_commit(sha)
            story.complete_story(
                story_id=story_id,
                commit=commit,
                load_story=store.load_story,
                save_story=store.save_story,
                now=now,
            )
            return f"completed {story_id_text(story_id)} at {commit.sha}\n"
        case UpkeepId() as upkeep_id:
            commit = make_commit(sha)
            upkeep.complete_upkeep(
                upkeep_id=upkeep_id,
                commit=commit,
                load_upkeep=store.load_upkeep,
                save_upkeep=store.save_upkeep,
                now=now,
            )
            return f"completed {upkeep_id_text(upkeep_id)} at {commit.sha}\n"
        case TaskId() as task_id:
            return _complete_task(task_id, sha, store, now)
        case _ as unreachable:
            assert_never(unreachable)
