"""The file of a Story in the record: one TOML file per Story, its Tasks inside it."""

import tomllib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, assert_never

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from flowgraph.criterion import make_commit, make_scenario
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
    completed_task,
    make_story,
    parse_story_id,
    started_story,
    started_task,
    state_name,
    story_id_text,
)
from flowgraph.task import (
    CompletedTask,
    StartedTask,
    Task,
    TaskRow,
    TaskState,
    make_task,
    parse_task_id,
    task_id_text,
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


class _CriterionFile(BaseModel):
    """The criterion table of a Story file."""

    model_config = ConfigDict(extra="forbid")

    given: str
    when: str
    then: str


class _TaskFile(BaseModel):
    """One table of the tasks of a Story file: a Task in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime


class _StartedTaskFile(BaseModel):
    """One table of the tasks of a started Story file: a started Task."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime
    started: datetime


class _CompletedTaskFile(BaseModel):
    """One table of the tasks of a Story file: a completed Task, with its commit."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["completed"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime
    started: datetime
    completed: datetime
    commit: str


# One table of the tasks of a started Story file, told apart by its state line.
_HeldTask = Annotated[
    _TaskFile | _StartedTaskFile | _CompletedTaskFile, Field(discriminator="state")
]


class _StoryFile(BaseModel):
    """What the file of a Story in Backlog holds: its Tasks are all in Backlog."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    created: datetime
    criterion: _CriterionFile
    tasks: list[_TaskFile] = []


class _StartedStoryFile(BaseModel):
    """What the file of a started Story holds: its started time, its Tasks in any state."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["started"]
    title: str
    description: str = ""
    created: datetime
    started: datetime
    criterion: _CriterionFile
    tasks: list[_HeldTask] = []


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
    criterion: _CriterionFile
    tasks: list[_CompletedTaskFile] = []


# The file of a Story in any of its states.
_HeldStoryFile = _StoryFile | _StartedStoryFile | _CompletedStoryFile

# The validator of a Story file, which tells the states apart by the state line.
_HELD_STORY: TypeAdapter[_HeldStoryFile] = TypeAdapter(
    Annotated[_HeldStoryFile, Field(discriminator="state")]
)


def _commit_held(
    held: _HeldStoryFile | _TaskFile | _StartedTaskFile | _CompletedTaskFile,
) -> str:
    """The commit a validated file or table holds; empty for an item not completed."""
    match held:
        case _CompletedStoryFile() | _CompletedTaskFile():
            return held.commit
        case _StoryFile() | _StartedStoryFile() | _TaskFile() | _StartedTaskFile():
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
        tasks=[
            TaskRow(
                task.id,
                task.title,
                task.expected_output,
                task.description,
                task.state,
                _commit_held(task),
            )
            for task in held.tasks
        ],
        commit=_commit_held(held),
    )


def read_task_ids(record: Path) -> list[str]:
    """Adapter: the ids of every Task in the record, as written, in no order.

    Raises StoryFileError naming the first file of a Story that does not hold one.
    """
    held = [_read_story_file(path) for path in (record / ITEMS).glob("ST-*.toml")]
    return [task.id for story in held for task in story.tasks]


def _moves_primitives(item: StoryState | TaskState) -> dict[str, object]:
    """The times and the commit of the moves an item has made, as its file holds them."""
    match item:
        case Story() | Task():
            return {}
        case StartedStory() | StartedTask():
            return {"started": item.started}
        case CompletedStory() | CompletedTask():
            return {"started": item.started, "completed": item.completed, "commit": item.commit.sha}
        case _ as unreachable:
            assert_never(unreachable)


def _task_primitives(task: TaskState) -> dict[str, object]:
    """The Task as the primitives its table holds; a description only when there is one."""
    described = {"description": task.description} if task.description else {}
    return {
        "id": task_id_text(task.id),
        "state": state_name(task),
        "title": task.title,
        **described,
        "expected_output": task.expected_output,
        "created": task.created,
        **_moves_primitives(task),
    }


def _story_primitives(story: StoryState) -> dict[str, object]:
    """The Story as the primitives its file holds; a description and tasks only when it has any."""
    described = {"description": story.description} if story.description else {}
    tasks = {"tasks": [_task_primitives(task) for task in story.tasks]} if story.tasks else {}
    return {
        "id": story_id_text(story.id),
        "state": state_name(story),
        "title": story.title,
        **described,
        "created": story.created,
        **_moves_primitives(story),
        "criterion": {
            "given": story.scenario.given,
            "when": story.scenario.when,
            "then": story.scenario.then,
        },
        **tasks,
    }


def _task_held(held: _TaskFile | _StartedTaskFile | _CompletedTaskFile) -> Task:
    """The Task a validated table holds, in Backlog, built through its constructors."""
    return make_task(
        parse_task_id(held.id), held.title, held.expected_output, held.description, held.created
    )


def _task_moved(
    story: StartedStory, held: _TaskFile | _StartedTaskFile | _CompletedTaskFile
) -> StartedStory:
    """The started Story with the Task of the table moved as far as the table says."""
    task_id = parse_task_id(held.id)
    match held:
        case _TaskFile():
            return story
        case _StartedTaskFile():
            return started_task(story, task_id, held.started)
        case _CompletedTaskFile():
            begun = started_task(story, task_id, held.started)
            return completed_task(begun, task_id, held.completed, make_commit(held.commit))
        case _ as unreachable:
            assert_never(unreachable)


def _story_held(held: _HeldStoryFile) -> StoryState:
    """The Story a validated file holds, with its Tasks, built through its constructors.

    A Story and its Tasks past Backlog are built by the moves that took them there, so a file
    holds no state those moves could not reach.
    """
    criterion = held.criterion
    scenario = make_scenario(criterion.given, criterion.when, criterion.then)
    story = make_story(
        parse_story_id(held.id), held.title, scenario, held.description, held.created
    )
    for task in held.tasks:
        story = append_task(story, _task_held(task))
    match held:
        case _StoryFile():
            return story
        case _StartedStoryFile() | _CompletedStoryFile():
            begun = started_story(story, held.started)
            for task in held.tasks:
                begun = _task_moved(begun, task)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    beside = path.with_name(f"{path.name}.tmp")
    beside.write_text(tomli_w.dumps(_story_primitives(story)), encoding="utf-8")
    if _story_held(_read_story_file(beside)) != story:
        beside.unlink()
        raise StoryMismatchError(f"{path}: the Story written reads back different")
    beside.replace(path)
