"""The file of a Story in the record: the work item file, read by the `ST-` prefix."""

from collections.abc import Callable
from pathlib import Path

from flowgraph import work_item
from flowgraph.story.model import STORY, StoryDetail, StoryId, StoryRow, StoryState

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

read_story = work_item.read_work_item
read_story_detail = work_item.read_work_item_detail
write_story = work_item.write_work_item


def read_story_rows(record: Path) -> list[StoryRow]:
    """Adapter: the rows of the stories in the record, by id; a file of another kind is left alone.

    Raises StoryFileError naming the first file of a Story that does not hold one.
    """
    return work_item.read_work_item_rows(record, STORY)


def read_task_ids(record: Path) -> list[str]:
    """Adapter: the ids of every Task of the stories in the record, as written, in no order.

    Raises StoryFileError naming the first file of a Story that does not hold one.
    """
    return work_item.read_task_ids(record, STORY)
