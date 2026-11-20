"""A Story: new behavior to build, kept in the record with its one Given / When / Then."""

import re
from collections.abc import Callable, Collection
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


class EmptyPartError(ValueError):
    """A part of a Story that must say something is blank; `part` names it."""

    def __init__(self, part: str) -> None:
        super().__init__(f"{part} is empty")
        self.part = part


class StoryIdError(ValueError):
    """A number or a text that is no Story id."""


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
    return Story(story_id, _said("title", title), scenario, description, to_the_second)


def story_row(story: Story) -> StoryRow:
    """The Story as the row a view reads."""
    return StoryRow(story_id_text(story.id), story.title, "backlog")


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


def read_story_rows(record: Path) -> list[StoryRow]:
    """Adapter: the rows of the stories in the record, by id."""
    raise NotImplementedError


def write_story(record: Path, story: Story) -> None:
    """Adapter: write the Story as its one file in the record."""
    raise NotImplementedError
