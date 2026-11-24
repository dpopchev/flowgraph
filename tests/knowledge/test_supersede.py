"""The lines a note supersedes, checked against the record, and the rows read back superseded."""

from datetime import UTC, datetime
from typing import NoReturn

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.knowledge import DECISION, KnowledgeRow, make_knowledge_line
from flowgraph.knowledge.supersede import LineRefError, superseded_rows, supersedes_asked
from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store
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
REFUSAL = (
    r"^--supersedes names {}, which is no knowledge line of the record: "
    r"fgraph knowledge lists each line with its ref$"
)


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
)
HELD = store_of(story(1, ("keep one store", ())))
ROWS = [KnowledgeRow("decision", NOW, "keep one store"), KnowledgeRow("decision", NOW, "keep it")]


def test_a_note_that_names_none_supersedes_none_and_reads_no_store() -> None:
    assert supersedes_asked(None, UNREAD) == ()


def test_a_ref_the_record_holds_is_given_back() -> None:
    assert supersedes_asked(["S-0001#1"], HELD) == ("S-0001#1",)


def test_a_ref_given_twice_is_kept_once() -> None:
    assert supersedes_asked(["S-0001#1", "S-0001#1"], HELD) == ("S-0001#1",)


def test_a_ref_in_a_short_spelling_of_its_id_is_read_as_the_ref() -> None:
    assert supersedes_asked(["s1#1"], HELD) == ("S-0001#1",)


@pytest.mark.parametrize("ref", ["S-0001#9", "S-0009#1", "S-0001", "T-0001#1", "x"])
def test_a_ref_that_names_no_line_of_the_record_is_refused_as_typed(ref: str) -> None:
    with pytest.raises(LineRefError, match=REFUSAL.format(ref)):
        supersedes_asked([ref], HELD)


def test_the_rows_of_an_item_are_each_superseded_by_the_lines_that_name_them() -> None:
    held = store_of(story(1, ("keep one store", ()), ("keep it", ("S-0001#1",))))
    rows = superseded_rows("S-0001", ROWS, held)
    assert [row.superseded_by for row in rows] == [["S-0001#2"], []]


def test_a_row_named_by_a_line_of_another_item_is_superseded_by_it() -> None:
    held = store_of(story(1, ("keep one store", ())), story(2, ("one file each", ("S-0001#1",))))
    assert superseded_rows("S-0001", ROWS, held)[0].superseded_by == ["S-0002#1"]


def test_no_row_is_given_back_with_the_store_never_read() -> None:
    assert superseded_rows("S-0001", [], UNREAD) == []
