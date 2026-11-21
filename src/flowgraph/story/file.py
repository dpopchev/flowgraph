"""The file of a Story in the record: one TOML file per Story, its Tasks inside it."""

import tomllib
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from flowgraph.criterion import make_commit
from flowgraph.item_file import (
    CompletedTaskFile,
    CriterionFile,
    HeldTask,
    TaskFile,
    backlog_task,
    criterion_primitives,
    scenario_held,
    task_held,
    task_primitives,
    task_row,
    write_checked,
)
from flowgraph.record import ITEMS
from flowgraph.story.model import (
    CompletedStory,
    StartedStory,
    Story,
    StoryDetail,
    StoryFileError,
    StoryId,
    StoryMismatchError,
    StoryNotFoundError,
    StoryRow,
    StoryState,
    append_task,
    completed_story,
    make_story,
    parse_story_id,
    started_story,
    state_name,
    story_id_text,
)

# The rows of the stories in the record at the path; an empty list when it holds none.
ReadStoryRows = Callable[[Path], list[StoryRow]]

# The Story of that id in the record at the path, whole; raises StoryNotFoundError when the
# record holds none.
ReadStory = Callable[[Path, StoryId], StoryState]

# The Story of that id in the record at the path, with its Tasks, as plain data; raises
# StoryNotFoundError when the record holds none.
ReadStoryDetail = Callable[[Path, StoryId], StoryDetail]

# The ids of every Task in the record at the path, as written; an empty list when it holds none.
ReadTaskIds = Callable[[Path], list[str]]

# Save the Story whole into the record at the path.
WriteStory = Callable[[Path, StoryState], None]


class _StoryFile(BaseModel):
    """What the file of a Story in Backlog holds: its Tasks are all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    created: datetime
    criterion: CriterionFile
    tasks: list[TaskFile] = []


class _StartedStoryFile(BaseModel):
    """What the file of a started Story holds: its started time, its Tasks in any state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    created: datetime
    started: datetime
    criterion: CriterionFile
    tasks: list[HeldTask] = []


class _CompletedStoryFile(BaseModel):
    """What the file of a completed Story holds: its commit, its Tasks all completed."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    created: datetime
    started: datetime
    completed: datetime
    commit: str
    criterion: CriterionFile
    tasks: list[CompletedTaskFile] = []


# The file of a Story in any of its states.
_HeldStoryFile = _StoryFile | _StartedStoryFile | _CompletedStoryFile

# The validator of a Story file, which tells the states apart by the state line.
_HELD_STORY: TypeAdapter[_HeldStoryFile] = TypeAdapter(
    Annotated[_HeldStoryFile, Field(discriminator="state")]
)


def _commit_held(held: _HeldStoryFile) -> str:
    """The commit a validated file or table holds; empty for an item not completed."""
    match held:
        case _CompletedStoryFile():
            return held.commit
        case _StoryFile() | _StartedStoryFile():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def _read_story_file(path: Path) -> _HeldStoryFile:
    """The content of one Story file; raises StoryFileError naming the path."""
    try:
        return _HELD_STORY.validate_python(tomllib.loads(path.read_text(encoding="utf-8")))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise StoryFileError(f"{path} holds no Story: {error}") from error


def read_story_rows(record: Path) -> list[StoryRow]:
    """Adapter: the rows of the stories in the record, by id.

    A Story is a file of the items named `ST-`; a file of another kind is left alone. Raises
    StoryFileError naming the first such file that does not hold a Story.
    """
    held = [_read_story_file(path) for path in (record / ITEMS).glob("ST-*.toml")]
    rows = [StoryRow(story.id, story.title, story.state, _commit_held(story)) for story in held]
    return sorted(rows, key=lambda row: parse_story_id(row.id).number)


def _held_path(record: Path, story_id: StoryId) -> Path:
    """The file of the Story of that id in the record; raises StoryNotFoundError without one."""
    path = record / ITEMS / f"{story_id_text(story_id)}.toml"
    if not path.is_file():
        raise StoryNotFoundError(story_id)
    return path


def read_story(record: Path, story_id: StoryId) -> StoryState:
    """Adapter: the Story of that id in the record, whole.

    Raises StoryNotFoundError when the record holds no such Story and StoryFileError when its
    file does not hold one.
    """
    return _story_held(_read_story_file(_held_path(record, story_id)))


def read_story_detail(record: Path, story_id: StoryId) -> StoryDetail:
    """Adapter: the Story of that id in the record, with its Tasks, as plain data.

    Raises StoryNotFoundError when the record holds no such Story and StoryFileError when its
    file does not hold one.
    """
    held = _read_story_file(_held_path(record, story_id))
    return StoryDetail(
        id=held.id,
        title=held.title,
        state=held.state,
        description=held.description,
        given=held.criterion.given,
        when=held.criterion.when,
        then=held.criterion.then,
        tasks=[task_row(task) for task in held.tasks],
        commit=_commit_held(held),
    )


def read_task_ids(record: Path) -> list[str]:
    """Adapter: the ids of every Task in the record, as written, in no order.

    Raises StoryFileError naming the first file of a Story that does not hold one.
    """
    held = [_read_story_file(path) for path in (record / ITEMS).glob("ST-*.toml")]
    return [task.id for story in held for task in story.tasks]


def _moves_primitives(item: StoryState) -> dict[str, object]:
    """The times and the commit of the moves an item has made, as its file holds them."""
    match item:
        case Story():
            return {}
        case StartedStory():
            return {"started": item.started}
        case CompletedStory():
            return {"started": item.started, "completed": item.completed, "commit": item.commit.sha}
        case _ as unreachable:
            assert_never(unreachable)


def _story_primitives(story: StoryState) -> dict[str, object]:
    """The Story as the primitives its file holds; a description and tasks only when it has any."""
    described = {"description": story.description} if story.description else {}
    tasks = {"tasks": [task_primitives(task) for task in story.tasks]} if story.tasks else {}
    return {
        "id": story_id_text(story.id),
        "state": state_name(story),
        "title": story.title,
        **described,
        "created": story.created,
        **_moves_primitives(story),
        "criterion": criterion_primitives(story.scenario),
        **tasks,
    }


def _story_held(held: _HeldStoryFile) -> StoryState:
    """The Story a validated file holds, with its Tasks, built through its constructors.

    A Story and its Tasks past Backlog are built by the moves that took them there, so a file
    holds no state those moves could not reach.
    """
    scenario = scenario_held(held.criterion)
    story = make_story(
        parse_story_id(held.id), held.title, scenario, held.description, held.created
    )
    for task in held.tasks:
        story = append_task(story, backlog_task(task))
    match held:
        case _StoryFile():
            return story
        case _StartedStoryFile() | _CompletedStoryFile():
            tasks = tuple(task_held(task) for task in held.tasks)
            begun = replace(started_story(story, held.started), tasks=tasks)
            match held:
                case _CompletedStoryFile():
                    return completed_story(begun, held.completed, make_commit(held.commit))
                case _StartedStoryFile():
                    return begun
                case _ as unreachable:
                    assert_never(unreachable)
        case _ as unreachable:
            assert_never(unreachable)


def write_story(record: Path, story: StoryState) -> None:
    """Adapter: write the Story as its one file in the record.

    The Story is written beside its file and read back before it replaces it. Raises
    StoryMismatchError naming the file when the Story read back differs; the file is then as
    it was before.
    """
    path = record / ITEMS / f"{story_id_text(story.id)}.toml"
    write_checked(
        path,
        _story_primitives(story),
        lambda beside: _story_held(_read_story_file(beside)) == story,
        StoryMismatchError(f"{path}: the Story written reads back different"),
    )
