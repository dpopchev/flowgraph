"""The views and the commands of a Story: each command loads it whole, moves it and saves it."""

from flowgraph.criterion import Commit, make_scenario
from flowgraph.record import Now
from flowgraph.story.model import (
    FindStoryRows,
    FindTaskIds,
    LoadStory,
    SaveStory,
    StoryDetail,
    StoryId,
    StoryRow,
    StoryState,
    append_task,
    commit_sha,
    completed_story,
    completed_task,
    make_story,
    next_story_id,
    parse_story_id,
    started_story,
    started_task,
    state_name,
    still_open,
    story_id_text,
)
from flowgraph.task import (
    TaskId,
    TaskNotFoundError,
    TaskRow,
    make_task,
    next_task_id,
    parse_task_id,
    task_id_text,
)


def story_row(story: StoryState) -> StoryRow:
    """The Story as the row a view reads."""
    return StoryRow(story_id_text(story.id), story.title, state_name(story), commit_sha(story))


def story_detail(story: StoryState) -> StoryDetail:
    """The Story with its criterion and its Tasks as the plain data a view reads."""
    return StoryDetail(
        id=story_id_text(story.id),
        title=story.title,
        state=state_name(story),
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
                state_name(task),
                commit_sha(task),
            )
            for task in story.tasks
        ],
        commit=commit_sha(story),
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
