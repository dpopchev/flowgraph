"""A Story: new behavior to build, kept in the record with its one Given / When / Then."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


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
class Story:
    """A Story in Backlog: added, not yet started."""

    id: StoryId
    title: str
    scenario: Scenario
    description: str
    created: datetime


@dataclass
class StoryRow:
    """One Story as plain data, as a view reads it from the record."""

    id: str
    title: str
    state: str


# The rows of the stories in the record; an empty list when it holds none.
FindStoryRows = Callable[[], list[StoryRow]]

# Save the Story whole.
SaveStory = Callable[[Story], None]

# The current time, with its zone.
Now = Callable[[], datetime]

# The rows of the stories in the record at the path; an empty list when it holds none.
ReadStoryRows = Callable[[Path], list[StoryRow]]

# Save the Story whole into the record at the path.
WriteStory = Callable[[Path, Story], None]


def story_row(story: Story) -> StoryRow:
    """The Story as the row a view reads."""
    raise NotImplementedError


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
    """Add a Story to Backlog under the next free id and return that id."""
    raise NotImplementedError


def read_story_rows(record: Path) -> list[StoryRow]:
    """Adapter: the rows of the stories in the record, by id."""
    raise NotImplementedError


def write_story(record: Path, story: Story) -> None:
    """Adapter: write the Story as its one file in the record."""
    raise NotImplementedError
