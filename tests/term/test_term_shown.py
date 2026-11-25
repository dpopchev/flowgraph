"""A term as fgraph show reads it: its relations, its items and its knowledge, as plain data."""

from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.record.queue import make_queue
from flowgraph.record.store import Store, TermStore
from flowgraph.term import Term, TermNotFoundError, make_term, relate
from flowgraph.term.item import show_term, term_shown, term_text

pytestmark = pytest.mark.view

ADDED = datetime(2026, 1, 1, tzinfo=UTC)
GATE = make_term("gate", "a check every deliverable passes", ADDED)
LANE = make_term("lane", "one work item in its own worktree", ADDED)
WORK_ITEM = make_term("work-item", "a unit of work", ADDED)


def never(*_: object) -> Never:
    """A read or a write of the record that a term never asks for."""
    raise AssertionError("a term reads and writes its own file and the names alone")


def store(held: list[Term]) -> Store:
    """The store of a record holding those terms and no item."""

    def load(name: str) -> Term:
        for term in held:
            if term.name == name:
                return term
        raise TermNotFoundError(name)

    return Store(
        find_work_item_rows=lambda _: [],
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=lambda: make_queue([]),
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        terms=TermStore(load, never, lambda: [term.name for term in held]),
    )


GATE_RELATED = relate(relate(GATE, "is-a", "check"), "part-of", "lane")
LANE_HELD = [relate(GATE, "part-of", "lane"), relate(WORK_ITEM, "is-a", "lane"), LANE]


def test_a_term_holds_what_it_is_a() -> None:
    assert term_shown("gate", store([GATE_RELATED, LANE])).is_a == ("check",)


def test_a_term_holds_what_it_is_part_of() -> None:
    assert term_shown("gate", store([GATE_RELATED, LANE])).part_of == ("lane",)


def test_a_term_holds_its_kinds_read_from_the_others() -> None:
    assert term_shown("lane", store(LANE_HELD)).kinds == ("work-item",)


def test_a_term_holds_its_parts_read_from_the_others() -> None:
    assert term_shown("lane", store(LANE_HELD)).parts == ("gate",)


def test_a_term_holds_its_meaning() -> None:
    assert term_shown("lane", store(LANE_HELD)).meaning == LANE.meaning


def test_a_term_holds_the_day_it_was_added() -> None:
    assert term_shown("lane", store(LANE_HELD)).added == ADDED


def test_a_record_with_no_item_holds_no_item_about_a_term() -> None:
    assert term_shown("gate", store([GATE])).items == ()


def test_a_record_with_no_item_holds_no_knowledge_about_a_term() -> None:
    assert term_shown("gate", store([GATE])).knowledge == ()


@pytest.mark.parametrize("name", ["gate", "lane"])
def test_the_text_of_a_term_shown_is_the_text_of_show(name: str) -> None:
    held = [GATE_RELATED, *LANE_HELD[1:]]
    assert term_text(term_shown(name, store(held))) == show_term(name, store(held))


def test_a_term_the_record_holds_none_of_is_not_found() -> None:
    with pytest.raises(TermNotFoundError):
        term_shown("gate", store([]))
