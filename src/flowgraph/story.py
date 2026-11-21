"""A Story: new behavior to build, kept in the record with its criterion and its Tasks."""

import re
import tomllib
from collections.abc import Callable, Collection
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Literal, assert_never

import tomli_w
from pydantic import BaseModel, ConfigDict, ValidationError

# The directory of every item inside a record, one file per work item, named by its id.
ITEMS = "items"


@dataclass(frozen=True)
class StoryId:
    """The identity of a Story: its number in the record, written `ST-0001`."""

    number: int


@dataclass(frozen=True)
class Scenario:
    """The one criterion of a Story: the initial state, the action and the expected state."""

    given: str
    when: str
    then: str


@dataclass(frozen=True)
class TaskId:
    """The identity of a Task: its number in the record, written `T-0001`."""

    number: int


@dataclass(frozen=True)
class Task:
    """A Task in Backlog: written, not yet started."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime


@dataclass(frozen=True)
class Story:
    """A Story in Backlog: added, not yet started, with the Tasks written for it so far."""

    id: StoryId
    title: str
    scenario: Scenario
    description: str
    created: datetime
    tasks: tuple[Task, ...]


@dataclass(frozen=True)
class StartedTask:
    """A Task in InProgress: started under its started Story, not yet completed."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    started: datetime


@dataclass(frozen=True)
class StartedStory:
    """A Story in InProgress: started with at least one Task, each in Backlog or started."""

    id: StoryId
    title: str
    scenario: Scenario
    description: str
    created: datetime
    started: datetime
    tasks: tuple[Task | StartedTask, ...]


# A Story in any of its states, as the record keeps it.
StoryState = Story | StartedStory


@dataclass
class StoryRow:
    """One Story as plain data, as a view reads it from the record."""

    id: str
    title: str
    state: str


@dataclass
class TaskRow:
    """One Task as plain data, as a view reads it from the record."""

    id: str
    title: str
    expected_output: str
    description: str
    state: str


@dataclass
class StoryDetail:
    """One Story with its criterion and its Tasks as plain data, as a view reads it whole."""

    id: str
    title: str
    state: str
    description: str
    given: str
    when: str
    then: str
    tasks: list[TaskRow]


# The rows of the stories in the record; an empty list when it holds none.
FindStoryRows = Callable[[], list[StoryRow]]

# The ids of every Task in the record, as written; an empty list when it holds none.
FindTaskIds = Callable[[], list[str]]

# The Story of that id, whole; raises StoryNotFoundError when the record holds none.
LoadStory = Callable[[StoryId], Story]

# Save the Story whole.
SaveStory = Callable[[Story], None]

# The current time, with its zone.
Now = Callable[[], datetime]

# The rows of the stories in the record at the path; an empty list when it holds none.
ReadStoryRows = Callable[[Path], list[StoryRow]]

# The Story of that id in the record at the path, whole; raises StoryNotFoundError when the
# record holds none.
ReadStory = Callable[[Path, StoryId], Story]

# The Story of that id in the record at the path, with its Tasks, as plain data; raises
# StoryNotFoundError when the record holds none.
ReadStoryDetail = Callable[[Path, StoryId], StoryDetail]

# The ids of every Task in the record at the path, as written; an empty list when it holds none.
ReadTaskIds = Callable[[Path], list[str]]

# Save the Story whole into the record at the path.
WriteStory = Callable[[Path, Story], None]


class EmptyPartError(ValueError):
    """A part of a Story that must say something is blank; `part` names it."""

    def __init__(self, part: str) -> None:
        super().__init__(f"{part} is empty")
        self.part = part


class StoryIdError(ValueError):
    """A number or a text that is no Story id."""


class TaskIdError(ValueError):
    """A number or a text that is no Task id."""


class StoryNotFoundError(Exception):
    """A record that holds no Story of the id asked for; `story_id` is that id."""

    def __init__(self, story_id: StoryId) -> None:
        super().__init__(f"no Story {story_id_text(story_id)} in the record")
        self.story_id = story_id


class StoryFileError(Exception):
    """A file named as a Story in a record that does not hold one; names its path."""


class StoryMismatchError(Exception):
    """A Story read back different from the one written; its file is as it was before."""


class ItemIdError(ValueError):
    """A text that is neither a Story id nor a Task id."""


class TaskNotFoundError(Exception):
    """A Task id that no Story holds; `task_id` is that id."""

    def __init__(self, task_id: TaskId) -> None:
        super().__init__(f"no Task {task_id_text(task_id)} in the record")
        self.task_id = task_id


class NoTaskError(ValueError):
    """A Story started without a Task written for it."""


class StartedAlreadyError(ValueError):
    """A Story or a Task started once more."""


class StoryInBacklogError(ValueError):
    """A Task started while its Story is still in Backlog."""


def make_story_id(number: int) -> StoryId:
    """The id of the Story with that number in the record.

    Raises StoryIdError when the number is below 1.
    """
    if number < 1:
        raise StoryIdError(f"a Story id counts from 1: {number} is below 1")
    return StoryId(number)


def story_id_text(story_id: StoryId) -> str:
    """The id as it is written: `ST-` and the number, at least four digits."""
    return f"ST-{story_id.number:04d}"


def parse_story_id(text: str) -> StoryId:
    """The id written as the text.

    Raises StoryIdError when the text is not `ST-` and a number.
    """
    written = re.fullmatch(r"ST-(\d+)", text)
    if written is None:
        raise StoryIdError(f"{text!r} is no Story id: it is ST- and a number")
    return make_story_id(int(written.group(1)))


def next_story_id(taken: Collection[StoryId]) -> StoryId:
    """The next free id: one above the highest taken, the first when none is."""
    return make_story_id(max((story_id.number for story_id in taken), default=0) + 1)


def _said(part: str, text: str) -> str:
    """The text of the part, which must say something; raises EmptyPartError naming it."""
    if not text.strip():
        raise EmptyPartError(part)
    return text


def make_scenario(given: str, when: str, then: str) -> Scenario:
    """The criterion of a Story.

    Raises EmptyPartError naming the first part that is blank.
    """
    return Scenario(_said("given", given), _said("when", when), _said("then", then))


def make_story(
    story_id: StoryId, title: str, scenario: Scenario, description: str, created: datetime
) -> Story:
    """A Story in Backlog, its created time kept to the second.

    Raises EmptyPartError when the title is blank.
    """
    to_the_second = created.replace(microsecond=0)
    return Story(story_id, _said("title", title), scenario, description, to_the_second, ())


def make_task_id(number: int) -> TaskId:
    """The id of the Task with that number in the record.

    Raises TaskIdError when the number is below 1.
    """
    if number < 1:
        raise TaskIdError(f"a Task id counts from 1: {number} is below 1")
    return TaskId(number)


def task_id_text(task_id: TaskId) -> str:
    """The id as it is written: `T-` and the number, at least four digits."""
    return f"T-{task_id.number:04d}"


def parse_task_id(text: str) -> TaskId:
    """The id written as the text.

    Raises TaskIdError when the text is not `T-` and a number.
    """
    written = re.fullmatch(r"T-(\d+)", text)
    if written is None:
        raise TaskIdError(f"{text!r} is no Task id: it is T- and a number")
    return make_task_id(int(written.group(1)))


def next_task_id(taken: Collection[TaskId]) -> TaskId:
    """The next free id: one above the highest taken, the first when none is."""
    return make_task_id(max((task_id.number for task_id in taken), default=0) + 1)


def make_task(
    task_id: TaskId, title: str, expected_output: str, description: str, created: datetime
) -> Task:
    """A Task in Backlog, its created time kept to the second.

    Raises EmptyPartError when the title or the expected output is blank.
    """
    said = _said("title", title), _said("output", expected_output)
    return Task(task_id, *said, description, created.replace(microsecond=0))


def parse_item_id(text: str) -> StoryId | TaskId:
    """The Story id or the Task id written as the text.

    Raises ItemIdError when the text is neither.
    """
    try:
        return parse_story_id(text)
    except StoryIdError:
        pass
    try:
        return parse_task_id(text)
    except TaskIdError:
        raise ItemIdError(f"{text!r} is no Story id or Task id") from None


def append_task[S: (Story, StartedStory)](story: S, task: Task) -> S:
    """The Story with the Task written for it, after the Tasks it already has."""
    return replace(story, tasks=(*story.tasks, task))


def started_story(story: StoryState, on: datetime) -> StartedStory:
    """The Story started on that time, kept to the second, its Tasks still in Backlog.

    Raises NoTaskError when the Story has no Task and StartedAlreadyError when it is started.
    """
    match story:
        case Story(tasks=()):
            raise NoTaskError(f"{story_id_text(story.id)} has no Task to start with")
        case Story():
            to_the_second = on.replace(microsecond=0)
            return StartedStory(
                story.id,
                story.title,
                story.scenario,
                story.description,
                story.created,
                to_the_second,
                story.tasks,
            )
        case StartedStory():
            raise StartedAlreadyError(f"{story_id_text(story.id)} is started already")
        case _ as unreachable:
            assert_never(unreachable)


def _started(task: Task | StartedTask, on: datetime) -> StartedTask:
    """The Task started on that time; raises StartedAlreadyError when it is started."""
    match task:
        case Task():
            return StartedTask(
                task.id,
                task.title,
                task.expected_output,
                task.description,
                task.created,
                on.replace(microsecond=0),
            )
        case StartedTask():
            raise StartedAlreadyError(f"{task_id_text(task.id)} is started already")
        case _ as unreachable:
            assert_never(unreachable)


def started_task(story: StoryState, task_id: TaskId, on: datetime) -> StartedStory:
    """The started Story with its Task of that id started on that time, kept to the second.

    Raises StoryInBacklogError when the Story is in Backlog, TaskNotFoundError when it holds no
    such Task, and StartedAlreadyError when the Task is started.
    """
    match story:
        case Story():
            task, held = task_id_text(task_id), story_id_text(story.id)
            raise StoryInBacklogError(f"{task} cannot start: {held} is in Backlog")
        case StartedStory():
            if all(task.id != task_id for task in story.tasks):
                raise TaskNotFoundError(task_id)
            tasks = tuple(_started(t, on) if t.id == task_id else t for t in story.tasks)
            return replace(story, tasks=tasks)
        case _ as unreachable:
            assert_never(unreachable)


def story_row(story: Story) -> StoryRow:
    """The Story as the row a view reads."""
    return StoryRow(story_id_text(story.id), story.title, "backlog")


def story_detail(story: Story) -> StoryDetail:
    """The Story with its criterion and its Tasks as the plain data a view reads."""
    return StoryDetail(
        id=story_id_text(story.id),
        title=story.title,
        state="backlog",
        description=story.description,
        given=story.scenario.given,
        when=story.scenario.when,
        then=story.scenario.then,
        tasks=[
            TaskRow(
                task_id_text(task.id), task.title, task.expected_output, task.description, "backlog"
            )
            for task in story.tasks
        ],
    )


def add_story(
    *,
    title: str,
    given: str,
    when: str,
    then: str,
    description: str,
    find_story_rows: FindStoryRows,
    save_story: SaveStory,
    now: Now,
) -> StoryId:
    """Add a Story to Backlog under the next free id and return that id.

    Raises EmptyPartError when the title or a part of the criterion is blank; nothing is saved.
    """
    taken = [parse_story_id(row.id) for row in find_story_rows()]
    story = make_story(
        next_story_id(taken), title, make_scenario(given, when, then), description, now()
    )
    save_story(story)
    return story.id


def add_task(
    *,
    parent: str,
    title: str,
    expected_output: str,
    description: str,
    load_story: LoadStory,
    find_task_ids: FindTaskIds,
    save_story: SaveStory,
    now: Now,
) -> TaskId:
    """Write a Task for the Story named as parent, under the next free id, and return that id.

    Raises StoryIdError when the parent is no Story id, StoryNotFoundError when the record holds
    no such Story, and EmptyPartError when the title or the expected output is blank; nothing is
    saved.
    """
    story = load_story(parse_story_id(parent))
    taken = [parse_task_id(text) for text in find_task_ids()]
    task = make_task(next_task_id(taken), title, expected_output, description, now())
    save_story(append_task(story, task))
    return task.id


class _CriterionFile(BaseModel):
    """The criterion table of a Story file."""

    model_config = ConfigDict(extra="forbid")

    given: str
    when: str
    then: str


class _TaskFile(BaseModel):
    """One table of the tasks of a Story file: a Task."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    expected_output: str
    created: datetime


class _StoryFile(BaseModel):
    """What the file of a Story holds, validated as it is read."""

    model_config = ConfigDict(extra="forbid")

    id: str
    state: Literal["backlog"]
    title: str
    description: str = ""
    created: datetime
    criterion: _CriterionFile
    tasks: list[_TaskFile] = []


def _read_story_file(path: Path) -> _StoryFile:
    """The content of one Story file; raises StoryFileError naming the path."""
    try:
        return _StoryFile.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise StoryFileError(f"{path} holds no Story: {error}") from error


def read_story_rows(record: Path) -> list[StoryRow]:
    """Adapter: the rows of the stories in the record, by id.

    A Story is a file of the items named `ST-`; a file of another kind is left alone. Raises
    StoryFileError naming the first such file that does not hold a Story.
    """
    held = [_read_story_file(path) for path in (record / ITEMS).glob("ST-*.toml")]
    rows = [StoryRow(story.id, story.title, story.state) for story in held]
    return sorted(rows, key=lambda row: parse_story_id(row.id).number)


def _held_path(record: Path, story_id: StoryId) -> Path:
    """The file of the Story of that id in the record; raises StoryNotFoundError without one."""
    path = record / ITEMS / f"{story_id_text(story_id)}.toml"
    if not path.is_file():
        raise StoryNotFoundError(story_id)
    return path


def read_story(record: Path, story_id: StoryId) -> Story:
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
            TaskRow(task.id, task.title, task.expected_output, task.description, task.state)
            for task in held.tasks
        ],
    )


def read_task_ids(record: Path) -> list[str]:
    """Adapter: the ids of every Task in the record, as written, in no order.

    Raises StoryFileError naming the first file of a Story that does not hold one.
    """
    held = [_read_story_file(path) for path in (record / ITEMS).glob("ST-*.toml")]
    return [task.id for story in held for task in story.tasks]


def _task_primitives(task: Task) -> dict[str, object]:
    """The Task as the primitives its table holds; a description only when there is one."""
    described = {"description": task.description} if task.description else {}
    return {
        "id": task_id_text(task.id),
        "state": "backlog",
        "title": task.title,
        **described,
        "expected_output": task.expected_output,
        "created": task.created,
    }


def _story_primitives(story: Story) -> dict[str, object]:
    """The Story as the primitives its file holds; a description and tasks only when it has any."""
    described = {"description": story.description} if story.description else {}
    tasks = {"tasks": [_task_primitives(task) for task in story.tasks]} if story.tasks else {}
    return {
        "id": story_id_text(story.id),
        "state": "backlog",
        "title": story.title,
        **described,
        "created": story.created,
        "criterion": {
            "given": story.scenario.given,
            "when": story.scenario.when,
            "then": story.scenario.then,
        },
        **tasks,
    }


def _task_held(held: _TaskFile) -> Task:
    """The Task a validated table holds, built through its constructors."""
    return make_task(
        parse_task_id(held.id), held.title, held.expected_output, held.description, held.created
    )


def _story_held(held: _StoryFile) -> Story:
    """The Story a validated file holds, with its Tasks, built through its constructors."""
    criterion = held.criterion
    scenario = make_scenario(criterion.given, criterion.when, criterion.then)
    story = make_story(
        parse_story_id(held.id), held.title, scenario, held.description, held.created
    )
    for task in held.tasks:
        story = append_task(story, _task_held(task))
    return story


def write_story(record: Path, story: Story) -> None:
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
