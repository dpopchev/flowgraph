"""A term named by its name: its add, its list and its view.

Each runs on the store of a record, as the commands of a work item do (`flowgraph.item.commands`).
"""

from dataclasses import dataclass, replace
from datetime import datetime

from flowgraph.feature import feature_detail
from flowgraph.item.commands import MESSAGE, Written
from flowgraph.knowledge.list import KnowledgeEntry, collected, newest_first
from flowgraph.parent import parse_feature_id
from flowgraph.record import Now
from flowgraph.record.store import KINDS, Store
from flowgraph.relation import Standing, closes_cycle
from flowgraph.term.model import TermError, make_term, named_by, relate
from flowgraph.work_item import parse_work_item_id


class TermExistsError(ValueError):
    """A term added under a name the record holds already."""


def add_term_item(name: str, meaning: str, store: Store, now: Now) -> Written:
    """Add the term of that name with that meaning; what the write says.

    Raises TermError when the name is no term name or reads as the id of an item, EmptyPartError
    when the meaning is blank and TermExistsError when the record holds the name already;
    nothing is saved then.
    """
    term = make_term(name, meaning, now())
    if name in store.terms.find_term_names():
        raise TermExistsError(f"the record holds the term {name!r} already")
    store.terms.save_term(term)
    return Written(f"added {name}\n", MESSAGE.format(f"add term {name}"))


def relate_term_item(first: str, kind: str, second: str, store: Store) -> Written:
    """Relate the first term to the second by that kind; what the write says.

    Raises TermNotFoundError for a term the record holds none of, TermError for a kind outside
    the set, a term related to itself, a relation kept already and a relation that would close a
    cycle of its kind; nothing is saved then.
    """
    term = store.terms.load_term(first)
    store.terms.load_term(second)
    related = relate(term, kind, second)
    names = store.terms.find_term_names()
    held = {name: store.terms.load_term(name) for name in names}
    standing = {name: Standing("", False, named_by(each, kind)) for name, each in held.items()}
    if closes_cycle(first, [second], standing):
        raise TermError(f"{first} {kind} {second} would close a cycle: {second} is {kind} {first}")
    store.terms.save_term(related)
    return Written(f"related {first} {kind} {second}\n", MESSAGE.format(f"relate {first}"))


@dataclass(frozen=True)
class TermShown:
    """The term of fgraph show as plain data: its relations, its items and its knowledge lines."""

    name: str
    meaning: str
    added: datetime
    is_a: tuple[str, ...]
    part_of: tuple[str, ...]
    kinds: tuple[str, ...]
    parts: tuple[str, ...]
    items: tuple[str, ...] = ()
    knowledge: tuple[KnowledgeEntry, ...] = ()


def _head_of(name: str, store: Store) -> TermShown:
    """The term of that name with its relations, and no item and no knowledge line yet."""
    term = store.terms.load_term(name)
    others = [store.terms.load_term(each) for each in sorted(store.terms.find_term_names())]
    return TermShown(
        term.name,
        term.meaning,
        term.added,
        tuple(term.is_a),
        tuple(term.part_of),
        tuple(each.name for each in others if name in each.is_a),
        tuple(each.name for each in others if name in each.part_of),
    )


def term_shown(name: str, store: Store) -> TermShown:
    """The term of that name with the items and the knowledge lines about it.

    Raises TermNotFoundError when the record holds no such term.
    """
    return replace(
        _head_of(name, store),
        items=tuple(items_about(name, store)),
        knowledge=tuple(newest_first(collected(store), None, name)),
    )


def _head_text(shown: TermShown) -> str:
    """The head of the text of a term: its meaning, its relations, its day added."""
    relations = [
        ("is a", ", ".join(shown.is_a)),
        ("part of", ", ".join(shown.part_of)),
        ("kinds", ", ".join(shown.kinds)),
        ("parts", ", ".join(shown.parts)),
    ]
    lines = "".join(f"  {label}  {named}\n" for label, named in relations if named)
    added = shown.added.date().isoformat()
    return f"{shown.name}\n  means  {shown.meaning}\n{lines}  added  {added}\n"


def term_text(shown: TermShown) -> str:
    """The text of the term: its head, then the items and the knowledge lines about it.

    The lines are the newest first, each with the id of its item. Nothing is listed for none.
    """
    items = ", ".join(shown.items)
    heading = "  knowledge\n" if shown.knowledge else ""
    return _head_text(shown) + "".join(
        [
            f"  items  {items}\n" if items else "",
            heading,
            *(
                f"    {line.item}  {line.kind}  {line.noted.date().isoformat()}  {line.text}\n"
                for line in shown.knowledge
            ),
        ]
    )


def terms_text(store: Store) -> str:
    """The lines fgraph terms writes: each term by name with its meaning, or one line for none."""
    names = sorted(store.terms.find_term_names())
    if not names:
        return "no terms in the record\n"
    terms = (store.terms.load_term(name) for name in names)
    return "".join(f"{term.name}  {term.meaning}\n" for term in terms)


def items_about(name: str, store: Store) -> list[str]:
    """The ids of the work items and Features of the record about the term of that name.

    The work items come first, by kind and number, then the Features.
    """
    details = [
        store.find_work_item_detail(parse_work_item_id(kind, row.id))
        for kind in KINDS
        for row in store.find_work_item_rows(kind)
    ]
    features = [
        feature_detail(store.features.load_feature(parse_feature_id(text)))
        for text in sorted(store.features.find_feature_ids())
    ]
    return [detail.id for detail in [*details, *features] if name in detail.about]


def term_head(name: str, store: Store) -> str:
    """The head of the text of the term of that name: its meaning, its relations, its day added.

    Raises TermNotFoundError when the record holds no such term.
    """
    return _head_text(_head_of(name, store))


def show_term(name: str, store: Store) -> str:
    """The text of the term of that name: its meaning and the day it was added.

    The items and the knowledge lines about it follow its relations, read from the record.
    Raises TermNotFoundError when the record holds no such term.
    """
    return term_text(term_shown(name, store))
