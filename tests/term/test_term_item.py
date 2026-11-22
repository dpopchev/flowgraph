"""A term named by its name: its add, its list and its view, on the store of a record."""

import re
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.item import Written
from flowgraph.queue import make_queue
from flowgraph.scope import OutOfScopeError, Scope, within
from flowgraph.store import Store, TermStore
from flowgraph.story import make_story_id
from flowgraph.term import Term, TermError, TermNotFoundError, make_term, relate
from flowgraph.term_item import (
    TermExistsError,
    add_term_item,
    relate_term_item,
    show_term,
    terms_text,
)

ADDED = datetime(2026, 1, 1, tzinfo=UTC)
GATE = make_term("gate", "a check every deliverable passes", ADDED)
WORK_ITEM = make_term("work-item", "a unit of work", ADDED)


def never(*_: object) -> Never:
    """A read or a write of the record that a term never asks for."""
    raise AssertionError("a term reads and writes its own file and the names alone")


def store(held: list[Term], saved: list[Term] | None = None) -> Store:
    """The store of a record holding those terms; it notes a term it saves."""
    kept = [] if saved is None else saved

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
        terms=TermStore(load, kept.append, lambda: [term.name for term in held]),
    )


@pytest.mark.command
def test_a_term_added_says_its_name_and_the_message_of_its_commit() -> None:
    added = add_term_item("gate", "a meaning", store([]), lambda: ADDED)
    assert added == Written("added gate\n", "chore: add term gate in the record")


@pytest.mark.command
def test_a_term_added_is_saved_with_its_meaning_and_the_time_it_was_added() -> None:
    saved: list[Term] = []
    add_term_item("gate", "a meaning", store([], saved), lambda: ADDED)
    assert saved == [Term("gate", "a meaning", ADDED)]


@pytest.mark.command
def test_a_name_the_record_holds_already_is_refused_by_name_and_nothing_is_saved() -> None:
    with pytest.raises(
        TermExistsError, match=re.escape("the record holds the term 'gate' already")
    ):
        add_term_item("gate", "another meaning", store([GATE]), lambda: ADDED)


@pytest.mark.command
def test_a_term_refused_is_not_saved() -> None:
    saved: list[Term] = []
    with pytest.raises(TermExistsError):
        add_term_item("gate", "another meaning", store([GATE], saved), lambda: ADDED)
    assert saved == []


@pytest.mark.command
def test_a_name_that_reads_as_the_id_of_an_item_is_refused() -> None:
    with pytest.raises(TermError, match="reads as the id of an item"):
        add_term_item("S-0001", "a meaning", store([]), lambda: ADDED)


@pytest.mark.command
def test_a_blank_meaning_is_refused_naming_the_part() -> None:
    with pytest.raises(EmptyPartError, match=re.escape("meaning is empty")):
        add_term_item("gate", " ", store([]), lambda: ADDED)


@pytest.mark.view
def test_the_terms_are_listed_by_name_each_with_its_meaning() -> None:
    assert terms_text(store([WORK_ITEM, GATE])) == (
        "gate  a check every deliverable passes\nwork-item  a unit of work\n"
    )


@pytest.mark.view
def test_a_record_with_no_term_says_so_in_one_line() -> None:
    assert terms_text(store([])) == "no terms in the record\n"


@pytest.mark.view
def test_a_term_is_shown_with_its_meaning_and_the_day_it_was_added() -> None:
    assert show_term("gate", store([GATE])) == (
        "gate\n  means  a check every deliverable passes\n  added  2026-01-01\n"
    )


@pytest.mark.view
def test_a_term_the_record_holds_none_of_is_refused_by_name() -> None:
    with pytest.raises(TermNotFoundError, match=re.escape("no term 'gate' in the record")):
        show_term("gate", store([]))


@pytest.mark.command
def test_a_term_saved_on_the_branch_of_a_work_item_is_refused_naming_it() -> None:
    scope = Scope("wi/S-0001-a-slug", make_story_id(1))
    with pytest.raises(OutOfScopeError, match="writes S-0001 alone"):
        within(store([]), lambda: scope, never).terms.save_term(GATE)


@pytest.mark.command
def test_a_term_refused_on_the_branch_of_a_work_item_is_not_saved() -> None:
    saved: list[Term] = []
    scope = Scope("wi/S-0001-a-slug", make_story_id(1))
    with pytest.raises(OutOfScopeError):
        within(store([], saved), lambda: scope, never).terms.save_term(GATE)
    assert saved == []


@pytest.mark.command
def test_a_term_saved_where_no_work_item_owns_the_branch_is_saved() -> None:
    saved: list[Term] = []
    within(store([], saved), lambda: None, never).terms.save_term(GATE)
    assert saved == [GATE]


LANE = make_term("lane", "one work item in its own worktree", ADDED)


@pytest.mark.command
def test_two_terms_related_say_it_and_the_message_of_the_commit() -> None:
    related = relate_term_item("gate", "part-of", "lane", store([GATE, LANE]))
    assert related == Written("related gate part-of lane\n", "chore: relate gate in the record")


@pytest.mark.command
def test_two_terms_related_save_the_first_with_the_relation() -> None:
    saved: list[Term] = []
    relate_term_item("gate", "part-of", "lane", store([GATE, LANE], saved))
    assert saved == [relate(GATE, "part-of", "lane")]


@pytest.mark.command
@pytest.mark.parametrize(
    ("first", "kind", "second", "said"),
    [
        ("gate", "owns", "lane", "'owns' is no kind of relation: is-a or part-of"),
        ("gate", "part-of", "gate", "gate cannot be part-of itself"),
        ("gate", "part-of", "none", "no term 'none' in the record"),
        ("none", "part-of", "lane", "no term 'none' in the record"),
    ],
    ids=["a-kind-outside-the-set", "itself", "no-second-term", "no-first-term"],
)
def test_a_relation_refused_says_why_and_saves_nothing(
    first: str, kind: str, second: str, said: str
) -> None:
    saved: list[Term] = []
    with pytest.raises((TermError, TermNotFoundError), match=re.escape(said)):
        relate_term_item(first, kind, second, store([GATE, LANE], saved))
    assert saved == []


@pytest.mark.command
def test_a_relation_kept_already_is_refused_and_saves_nothing() -> None:
    saved: list[Term] = []
    held = [relate(GATE, "part-of", "lane"), LANE]
    with pytest.raises(TermError, match=re.escape("gate is part-of lane already")):
        relate_term_item("gate", "part-of", "lane", store(held, saved))
    assert saved == []


@pytest.mark.command
@pytest.mark.parametrize("kind", ["is-a", "part-of"])
def test_a_relation_that_closes_a_cycle_of_its_kind_is_refused_and_saves_nothing(
    kind: str,
) -> None:
    saved: list[Term] = []
    held = [relate(LANE, kind, "work-item"), relate(WORK_ITEM, kind, "gate"), GATE]
    with pytest.raises(TermError, match=re.escape(f"gate {kind} lane would close a cycle")):
        relate_term_item("gate", kind, "lane", store(held, saved))
    assert saved == []


@pytest.mark.command
def test_a_relation_of_another_kind_than_the_cycle_is_saved() -> None:
    saved: list[Term] = []
    held = [relate(LANE, "part-of", "gate"), GATE]
    relate_term_item("gate", "is-a", "lane", store(held, saved))
    assert saved == [relate(GATE, "is-a", "lane")]


@pytest.mark.view
def test_a_term_is_shown_with_what_it_is_a_and_what_it_is_part_of() -> None:
    gate = relate(relate(GATE, "is-a", "check"), "part-of", "lane")
    assert show_term("gate", store([gate, LANE])).splitlines()[2:4] == [
        "  is a  check",
        "  part of  lane",
    ]


@pytest.mark.view
def test_a_term_is_shown_with_its_kinds_and_its_parts_read_from_the_others() -> None:
    held = [relate(GATE, "part-of", "lane"), relate(WORK_ITEM, "is-a", "lane"), LANE]
    assert show_term("lane", store(held)).splitlines()[2:4] == [
        "  kinds  work-item",
        "  parts  gate",
    ]
