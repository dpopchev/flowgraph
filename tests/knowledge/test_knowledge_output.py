"""The output of fgraph knowledge: the format is chosen before the record is read, and the two
formats print the one list of lines."""

from datetime import UTC, datetime
from typing import NoReturn

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.knowledge import DECISION, make_knowledge_line
from flowgraph.knowledge.document import (
    JSON,
    TEXT,
    KnowledgeFormatError,
    knowledge_json,
    knowledge_output,
)
from flowgraph.knowledge.list import listed_knowledge, show_knowledge
from flowgraph.record.queue import make_queue
from flowgraph.record.store import FeatureStore, Store, TermStore
from flowgraph.story import (
    StoryId,
    StoryNotFoundError,
    StoryState,
    make_story,
    make_story_id,
    story_detail,
    story_id_text,
    story_row,
)
from flowgraph.work_item import noted_work_item

pytestmark = pytest.mark.view

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = make_scenario("a state", "an action", "another")


def story(number: int, *lines: tuple[str, tuple[str, ...]]) -> StoryState:
    """The Story of that number with a line of each text, superseding the refs given with it."""
    made: StoryState = make_story(make_story_id(number), "a title", CRITERION, "", NOW)
    for text, refs in lines:
        made = noted_work_item(made, make_knowledge_line(DECISION, text, NOW, supersedes=refs))
    return made


def store_of(*stories: StoryState) -> Store:
    """A store whose Stories are the ones given, by id; it holds no Feature."""
    saved = {story_id_text(each.id): each for each in stories}

    def held(story_id: StoryId) -> StoryState:
        if story_id_text(story_id) not in saved:
            raise StoryNotFoundError(story_id)
        return saved[story_id_text(story_id)]

    return Store(
        find_work_item_rows=lambda kind: [
            story_row(each) for each in saved.values() if each.id.kind == kind
        ],
        load_work_item=held,
        find_work_item_detail=lambda story_id: story_detail(held(story_id)),
        find_task_ids=lambda: [],
        save_work_item=lambda _: None,
        load_queue=lambda: make_queue([]),
        save_queue=lambda _: None,
        find_changed_files=lambda: [],
        restore_files=lambda: None,
    )


def unread(*_: object) -> NoReturn:
    """A read of the store that must not happen."""
    raise AssertionError("the store was read")


# A store whose every read raises.
UNREAD = Store(
    find_work_item_rows=unread,
    load_work_item=unread,
    find_work_item_detail=unread,
    find_task_ids=unread,
    save_work_item=unread,
    load_queue=unread,
    save_queue=unread,
    find_changed_files=unread,
    restore_files=unread,
    features=FeatureStore(unread, unread, unread),
    terms=TermStore(unread, unread, unread),
)
HELD = store_of(story(1, ("keep one store", ()), ("the store is plain", ())))


def test_a_format_that_is_neither_is_refused_before_the_record_is_read() -> None:
    with pytest.raises(KnowledgeFormatError, match="--format 'xml' is not text or json"):
        knowledge_output("xml", None, None, UNREAD)


def test_the_lines_of_two_decisions_noted_at_one_time_are_listed_newest_first() -> None:
    assert [entry.ref for entry in listed_knowledge(None, None, HELD)] == [
        "S-0001#2",
        "S-0001#1",
    ]


def test_the_json_output_is_the_json_of_the_lines_listed_for_the_same_options() -> None:
    assert knowledge_output(JSON, "decision", None, HELD) == knowledge_json(
        listed_knowledge("decision", None, HELD)
    )


def test_the_text_output_is_the_text_show_knowledge_prints() -> None:
    assert knowledge_output(TEXT, None, None, HELD) == show_knowledge(None, None, HELD)
