"""A Story: new behavior to build, kept in the record with its criterion and its Tasks."""

import re
import tomllib
from collections.abc import Callable, Collection
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, assert_never

import tomli_w
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

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
class Commit:
    """The commit that holds the work of an item: its sha, 7 to 40 hex digits."""

    sha: str


@dataclass(frozen=True)
class CompletedTask:
    """A Task in Completed: its work is in its commit."""

    id: TaskId
    title: str
    expected_output: str
    description: str
    created: datetime
    started: datetime
    completed: datetime
    commit: Commit


# A Task in any of its states, as the file of its Story keeps it.
TaskState = Task | StartedTask | CompletedTask


@dataclass(frozen=True)
class StartedStory:
    """A Story in InProgress: started with at least one Task, each in any state of its own."""

    id: StoryId
    title: str
    scenario: Scenario
    description: str
    created: datetime
    started: datetime
    tasks: tuple[TaskState, ...]


@dataclass(frozen=True)
class CompletedStory:
    """A Story in Completed: every Task of it completed, the Story in its commit on `main`."""

    id: StoryId
    title: str
    scenario: Scenario
    description: str
    created: datetime
    started: datetime
    completed: datetime
    commit: Commit
    tasks: tuple[CompletedTask, ...]


# A Story that still takes Tasks: in Backlog or started.
OpenStory = Story | StartedStory

# A Story in any of its states, as the record keeps it.
StoryState = Story | StartedStory | CompletedStory


@dataclass
class StoryRow:
    """One Story as plain data, as a view reads it from the record; a commit once completed."""

    id: str
    title: str
    state: str
    commit: str = ""


@dataclass
class TaskRow:
    """One Task as plain data, as a view reads it from the record; a commit once completed."""

    id: str
    title: str
    expected_output: str
    description: str
    state: str
    commit: str = ""


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
    commit: str = ""


# The rows of the stories in the record; an empty list when it holds none.
FindStoryRows = Callable[[], list[StoryRow]]

# The ids of every Task in the record, as written; an empty list when it holds none.
FindTaskIds = Callable[[], list[str]]

# The Story of that id, whole; raises StoryNotFoundError when the record holds none.
LoadStory = Callable[[StoryId], StoryState]

# Save the Story whole.
SaveStory = Callable[[StoryState], None]

# The current time, with its zone.
Now = Callable[[], datetime]

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


class CommitError(ValueError):
    """A text that is no commit sha."""


class CompletedAlreadyError(ValueError):
    """A completed Story or Task moved once more, or a Task written for a completed Story."""


class NotStartedError(ValueError):
    """A Story or a Task completed while it is still in Backlog."""


class OpenTaskError(ValueError):
    """A Story completed while some of its Tasks are not."""


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


def make_commit(text: str) -> Commit:
    """The commit of that sha.

    Raises CommitError when the text is not 7 to 40 lowercase hex digits.
    """
    if re.fullmatch(r"[0-9a-f]{7,40}", text) is None:
        raise CommitError(f"{text!r} is no commit: it is 7 to 40 hex digits")
    return Commit(text)


def append_task[S: OpenStory](story: S, task: Task) -> S:
    """The Story with the Task written for it, after the Tasks it already has."""
    return replace(story, tasks=(*story.tasks, task))


def still_open(story: StoryState) -> OpenStory:
    """The Story, which still takes Tasks; raises CompletedAlreadyError when it is completed."""
    match story:
        case Story() | StartedStory():
            return story
        case CompletedStory():
            raise CompletedAlreadyError(f"{story_id_text(story.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def _task_of(story: StoryState, task_id: TaskId) -> TaskState:
    """The Task of that id in the Story; raises TaskNotFoundError when it holds none."""
    held = [task for task in story.tasks if task.id == task_id]
    if not held:
        raise TaskNotFoundError(task_id)
    return held[0]


def started_story(story: StoryState, on: datetime) -> StartedStory:
    """The Story started on that time, kept to the second, its Tasks still in Backlog.

    Raises NoTaskError when the Story has no Task, StartedAlreadyError when it is started and
    CompletedAlreadyError when it is completed.
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
        case CompletedStory():
            raise CompletedAlreadyError(f"{story_id_text(story.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def _started(task: TaskState, on: datetime) -> StartedTask:
    """The Task started on that time.

    Raises StartedAlreadyError when it is started and CompletedAlreadyError when it is completed.
    """
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
        case CompletedTask():
            raise CompletedAlreadyError(f"{task_id_text(task.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def started_task(story: StoryState, task_id: TaskId, on: datetime) -> StartedStory:
    """The started Story with its Task of that id started on that time, kept to the second.

    Raises TaskNotFoundError when the Story holds no such Task, StoryInBacklogError when the
    Story is in Backlog, StartedAlreadyError when the Task is started and CompletedAlreadyError
    when it is completed.
    """
    _task_of(story, task_id)
    task = task_id_text(task_id)
    match story:
        case Story():
            raise StoryInBacklogError(
                f"{task} cannot start: {story_id_text(story.id)} is in Backlog"
            )
        case StartedStory():
            tasks = tuple(_started(t, on) if t.id == task_id else t for t in story.tasks)
            return replace(story, tasks=tasks)
        case CompletedStory():
            raise CompletedAlreadyError(f"{task} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def _completed(task: TaskState, on: datetime, commit: Commit) -> CompletedTask:
    """The Task completed on that time in that commit.

    Raises NotStartedError when it is in Backlog and CompletedAlreadyError when it is completed.
    """
    match task:
        case Task():
            raise NotStartedError(f"{task_id_text(task.id)} is in Backlog: start it first")
        case StartedTask():
            return CompletedTask(
                task.id,
                task.title,
                task.expected_output,
                task.description,
                task.created,
                task.started,
                on.replace(microsecond=0),
                commit,
            )
        case CompletedTask():
            raise CompletedAlreadyError(f"{task_id_text(task.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def completed_task(
    story: StoryState, task_id: TaskId, on: datetime, commit: Commit
) -> StartedStory:
    """The started Story with its Task of that id completed on that time, in that commit.

    Raises TaskNotFoundError when the Story holds no such Task, NotStartedError when the Task is
    in Backlog and CompletedAlreadyError when it is completed.
    """
    _task_of(story, task_id)
    task = task_id_text(task_id)
    match story:
        case Story():
            raise NotStartedError(f"{task} is in Backlog: start it first")
        case StartedStory():
            done = tuple(_completed(t, on, commit) if t.id == task_id else t for t in story.tasks)
            return replace(story, tasks=done)
        case CompletedStory():
            raise CompletedAlreadyError(f"{task} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def completed_story(story: StoryState, on: datetime, commit: Commit) -> CompletedStory:
    """The Story completed on that time, kept to the second, in that commit.

    Raises NotStartedError when it is in Backlog, OpenTaskError naming the Tasks not completed,
    and CompletedAlreadyError when it is completed.
    """
    match story:
        case Story():
            raise NotStartedError(f"{story_id_text(story.id)} is in Backlog: start it first")
        case StartedStory():
            done = tuple(task for task in story.tasks if isinstance(task, CompletedTask))
            left = [task_id_text(t.id) for t in story.tasks if not isinstance(t, CompletedTask)]
            if left:
                held = story_id_text(story.id)
                raise OpenTaskError(f"{held} has Tasks to complete first: {', '.join(left)}")
            return CompletedStory(
                story.id,
                story.title,
                story.scenario,
                story.description,
                story.created,
                story.started,
                on.replace(microsecond=0),
                commit,
                done,
            )
        case CompletedStory():
            raise CompletedAlreadyError(f"{story_id_text(story.id)} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def _state_of(item: StoryState | TaskState) -> str:
    """The state of a Story or a Task as the record writes it."""
    match item:
        case Story() | Task():
            return "backlog"
        case StartedStory() | StartedTask():
            return "started"
        case CompletedStory() | CompletedTask():
            return "completed"
        case _ as unreachable:
            assert_never(unreachable)


def _commit_of(item: StoryState | TaskState) -> str:
    """The sha of the commit of a completed Story or Task; empty for one not completed."""
    match item:
        case CompletedStory() | CompletedTask():
            return item.commit.sha
        case Story() | Task() | StartedStory() | StartedTask():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def story_row(story: StoryState) -> StoryRow:
    """The Story as the row a view reads."""
    return StoryRow(story_id_text(story.id), story.title, _state_of(story), _commit_of(story))


def story_detail(story: StoryState) -> StoryDetail:
    """The Story with its criterion and its Tasks as the plain data a view reads."""
    return StoryDetail(
        id=story_id_text(story.id),
        title=story.title,
        state=_state_of(story),
        description=story.description,
        given=story.scenario.given,
        when=story.scenario.when,
        then=story.scenario.then,
        tasks=[
            TaskRow(
                task_id_text(task.id),
                task.title,
                task.expected_output,
                task.description,
                _state_of(task),
                _commit_of(task),
            )
            for task in story.tasks
        ],
        commit=_commit_of(story),
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
    no such Story, CompletedAlreadyError when it is completed, and EmptyPartError when the title
    or the expected output is blank; nothing is saved.
    """
    story = still_open(load_story(parse_story_id(parent)))
    taken = [parse_task_id(text) for text in find_task_ids()]
    task = make_task(next_task_id(taken), title, expected_output, description, now())
    save_story(append_task(story, task))
    return task.id


def start_story(
    *, story_id: StoryId, load_story: LoadStory, save_story: SaveStory, now: Now
) -> None:
    """Start the Story of that id now and save it whole.

    Raises StoryNotFoundError when the record holds no such Story, NoTaskError when it has no
    Task and StartedAlreadyError when it is started; nothing is saved.
    """
    save_story(started_story(load_story(story_id), now()))


def start_task(
    *,
    task_id: TaskId,
    find_story_rows: FindStoryRows,
    load_story: LoadStory,
    save_story: SaveStory,
    now: Now,
) -> StoryId:
    """Start the Task of that id now, save its Story whole and return the id of that Story.

    Raises TaskNotFoundError when no Story holds the Task, StoryInBacklogError when its Story is
    in Backlog, StartedAlreadyError when it is started and CompletedAlreadyError when it is
    completed; nothing is saved.
    """
    story = _holder(task_id, find_story_rows, load_story)
    save_story(started_task(story, task_id, now()))
    return story.id


def _holder(task_id: TaskId, find_story_rows: FindStoryRows, load_story: LoadStory) -> StoryState:
    """The Story that holds the Task of that id; raises TaskNotFoundError when none does."""
    for row in find_story_rows():
        story = load_story(parse_story_id(row.id))
        if any(task.id == task_id for task in story.tasks):
            return story
    raise TaskNotFoundError(task_id)


def complete_story(
    *, story_id: StoryId, commit: Commit, load_story: LoadStory, save_story: SaveStory, now: Now
) -> None:
    """Complete the Story of that id now in that commit and save it whole.

    Raises StoryNotFoundError when the record holds no such Story, NotStartedError when it is in
    Backlog, OpenTaskError when a Task of it is not completed and CompletedAlreadyError when it
    is completed; nothing is saved.
    """
    save_story(completed_story(load_story(story_id), now(), commit))


def complete_task(
    *,
    task_id: TaskId,
    commit: Commit,
    find_story_rows: FindStoryRows,
    load_story: LoadStory,
    save_story: SaveStory,
    now: Now,
) -> StoryId:
    """Complete the Task of that id now in that commit, save its Story whole and return its id.

    Raises TaskNotFoundError when no Story holds the Task, NotStartedError when it is in Backlog
    and CompletedAlreadyError when it is completed; nothing is saved.
    """
    story = _holder(task_id, find_story_rows, load_story)
    save_story(completed_task(story, task_id, now(), commit))
    return story.id


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
        "state": _state_of(task),
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
        "state": _state_of(story),
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
