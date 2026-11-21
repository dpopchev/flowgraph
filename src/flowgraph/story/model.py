"""A Story: new behavior to build, its states, its Tasks and the moves between them."""

import re
from collections.abc import Callable, Collection
from dataclasses import dataclass, replace
from datetime import datetime
from typing import assert_never

from flowgraph.criterion import Commit, Scenario, said
from flowgraph.task import (
    CompletedAlreadyError,
    CompletedTask,
    NotStartedError,
    StartedAlreadyError,
    StartedTask,
    Task,
    TaskId,
    TaskIdError,
    TaskRow,
    TaskState,
    all_completed,
    completed_among,
    parse_task_id,
    started_among,
    task_id_text,
    task_of,
)


@dataclass(frozen=True)
class StoryId:
    """The identity of a Story: its number in the record, written `ST-0001`."""

    number: int


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


class StoryIdError(ValueError):
    """A number or a text that is no Story id."""


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


class NoTaskError(ValueError):
    """A Story started without a Task written for it."""


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


def make_story(
    story_id: StoryId, title: str, scenario: Scenario, description: str, created: datetime
) -> Story:
    """A Story in Backlog, its created time kept to the second.

    Raises EmptyPartError when the title is blank.
    """
    to_the_second = created.replace(microsecond=0)
    return Story(story_id, said("title", title), scenario, description, to_the_second, ())


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


def started_task(story: StoryState, task_id: TaskId, on: datetime) -> StartedStory:
    """The started Story with its Task of that id started on that time, kept to the second.

    Raises TaskNotFoundError when the Story holds no such Task, StoryInBacklogError when the
    Story is in Backlog, StartedAlreadyError when the Task is started and CompletedAlreadyError
    when it is completed.
    """
    task_of(story.tasks, task_id)
    task = task_id_text(task_id)
    match story:
        case Story():
            raise StoryInBacklogError(
                f"{task} cannot start: {story_id_text(story.id)} is in Backlog"
            )
        case StartedStory():
            return replace(story, tasks=started_among(story.tasks, task_id, on))
        case CompletedStory():
            raise CompletedAlreadyError(f"{task} is completed already")
        case _ as unreachable:
            assert_never(unreachable)


def completed_task(
    story: StoryState, task_id: TaskId, on: datetime, commit: Commit
) -> StartedStory:
    """The started Story with its Task of that id completed on that time, in that commit.

    Raises TaskNotFoundError when the Story holds no such Task, NotStartedError when the Task is
    in Backlog and CompletedAlreadyError when it is completed.
    """
    task_of(story.tasks, task_id)
    task = task_id_text(task_id)
    match story:
        case Story():
            raise NotStartedError(f"{task} is in Backlog: start it first")
        case StartedStory():
            return replace(story, tasks=completed_among(story.tasks, task_id, on, commit))
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
            done = all_completed(story.tasks, story_id_text(story.id))
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


def state_name(item: StoryState | TaskState) -> str:
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


def commit_sha(item: StoryState | TaskState) -> str:
    """The sha of the commit of a completed Story or Task; empty for one not completed."""
    match item:
        case CompletedStory() | CompletedTask():
            return item.commit.sha
        case Story() | Task() | StartedStory() | StartedTask():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
