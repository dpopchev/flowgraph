"""A Story: new behavior to build, the kind of work item whose ids are written `ST-0001`.

Each Story name stands for the name of the shared work item (`flowgraph.work_item`).
"""

from collections.abc import Collection

from flowgraph.work_item import (
    CompletedWorkItem,
    FindWorkItemRows,
    LoadWorkItem,
    OpenWorkItem,
    SaveWorkItem,
    StartedWorkItem,
    WorkItem,
    WorkItemDetail,
    WorkItemFileError,
    WorkItemId,
    WorkItemIdError,
    WorkItemMismatchError,
    WorkItemNotFoundError,
    WorkItemRow,
    WorkItemState,
    completed_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    next_work_item_id,
    parse_work_item_id,
    started_work_item,
    work_item_id_text,
)

# The kind of a Story.
STORY = make_kind("Story", "a", "ST")

StoryId = WorkItemId
Story = WorkItem
StartedStory = StartedWorkItem
CompletedStory = CompletedWorkItem
OpenStory = OpenWorkItem
StoryState = WorkItemState
StoryRow = WorkItemRow
StoryDetail = WorkItemDetail
FindStoryRows = FindWorkItemRows
LoadStory = LoadWorkItem
SaveStory = SaveWorkItem
StoryIdError = WorkItemIdError
StoryNotFoundError = WorkItemNotFoundError
StoryFileError = WorkItemFileError
StoryMismatchError = WorkItemMismatchError

make_story = make_work_item
started_story = started_work_item
completed_story = completed_work_item
story_id_text = work_item_id_text


def make_story_id(number: int) -> StoryId:
    """The id of the Story with that number; raises StoryIdError when it is below 1."""
    return make_work_item_id(STORY, number)


def parse_story_id(text: str) -> StoryId:
    """The Story id written as the text; raises StoryIdError when it is not `ST-` and a number."""
    return parse_work_item_id(STORY, text)


def next_story_id(taken: Collection[StoryId]) -> StoryId:
    """The next free Story id: one above the highest taken, the first when none is."""
    return next_work_item_id(STORY, taken)
