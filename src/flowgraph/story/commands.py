"""The views and the commands of a Story: the work item commands, on the stories of the record."""

from flowgraph import work_item
from flowgraph.criterion import Commit
from flowgraph.record import Now
from flowgraph.story.model import (
    STORY,
    FindStoryRows,
    LoadStory,
    SaveStory,
    StoryId,
    parse_story_id,
)
from flowgraph.task import TaskId

story_row = work_item.work_item_row
story_detail = work_item.work_item_detail


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
    return work_item.add_work_item(
        kind=STORY,
        title=title,
        given=given,
        when=when,
        then=then,
        description=description,
        find_work_item_rows=find_story_rows,
        save_work_item=save_story,
        now=now,
    )


def add_task(
    *,
    parent: str,
    title: str,
    expected_output: str,
    description: str,
    load_story: LoadStory,
    find_task_ids: work_item.FindTaskIds,
    save_story: SaveStory,
    now: Now,
) -> TaskId:
    """Write a Task for the Story named as parent, under the next free id, and return that id.

    Raises StoryIdError when the parent is no Story id, StoryNotFoundError when the record holds
    no such Story, CompletedAlreadyError when it is completed, and EmptyPartError when the title
    or the expected output is blank; nothing is saved.
    """
    return work_item.add_task(
        parent=parse_story_id(parent),
        title=title,
        expected_output=expected_output,
        description=description,
        load_work_item=load_story,
        find_task_ids=find_task_ids,
        save_work_item=save_story,
        now=now,
    )


def start_story(
    *, story_id: StoryId, load_story: LoadStory, save_story: SaveStory, now: Now
) -> None:
    """Start the Story of that id now and save it whole.

    Raises StoryNotFoundError when the record holds no such Story, NoTaskError when it has no
    Task and StartedAlreadyError when it is started; nothing is saved.
    """
    work_item.start_work_item(
        item_id=story_id, load_work_item=load_story, save_work_item=save_story, now=now
    )


def _load_holder(find_story_rows: FindStoryRows, load_story: LoadStory) -> work_item.LoadHolder:
    """The load of the Story that holds a Task, among the stories of the record."""
    return lambda task_id: work_item.holder_of(
        task_id, [parse_story_id(row.id) for row in find_story_rows()], load_story
    )


def start_task(
    *,
    task_id: TaskId,
    find_story_rows: FindStoryRows,
    load_story: LoadStory,
    save_story: SaveStory,
    now: Now,
) -> StoryId:
    """Start the Task of that id now, save its Story whole and return the id of that Story.

    Raises TaskNotFoundError when no Story holds the Task, ItemInBacklogError when its Story is
    in Backlog, StartedAlreadyError when it is started and CompletedAlreadyError when it is
    completed; nothing is saved.
    """
    return work_item.start_task(
        task_id=task_id,
        load_holder=_load_holder(find_story_rows, load_story),
        save_work_item=save_story,
        now=now,
    )


def complete_story(
    *, story_id: StoryId, commit: Commit, load_story: LoadStory, save_story: SaveStory, now: Now
) -> None:
    """Complete the Story of that id now in that commit and save it whole.

    Raises StoryNotFoundError when the record holds no such Story, NotStartedError when it is in
    Backlog, OpenTaskError when a Task of it is not completed and CompletedAlreadyError when it
    is completed; nothing is saved.
    """
    work_item.complete_work_item(
        item_id=story_id,
        commit=commit,
        load_work_item=load_story,
        save_work_item=save_story,
        now=now,
    )


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
    return work_item.complete_task(
        task_id=task_id,
        commit=commit,
        load_holder=_load_holder(find_story_rows, load_story),
        save_work_item=save_story,
        now=now,
    )
