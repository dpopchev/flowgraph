"""A term named by its name: its add, its list and its view.

Each runs on the store of a record, as the commands of a work item do (`flowgraph.item`).
"""

from flowgraph.item import MESSAGE, Written
from flowgraph.record import Now
from flowgraph.relation import Standing, closes_cycle
from flowgraph.store import Store
from flowgraph.term import TermError, make_term, named_by, relate


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


def terms_text(store: Store) -> str:
    """The lines fgraph terms writes: each term by name with its meaning, or one line for none."""
    names = sorted(store.terms.find_term_names())
    if not names:
        return "no terms in the record\n"
    terms = (store.terms.load_term(name) for name in names)
    return "".join(f"{term.name}  {term.meaning}\n" for term in terms)


def show_term(name: str, store: Store) -> str:
    """The text of the term of that name: its meaning and the day it was added.

    Raises TermNotFoundError when the record holds no such term.
    """
    term = store.terms.load_term(name)
    others = [store.terms.load_term(each) for each in sorted(store.terms.find_term_names())]
    relations = [
        ("is a", ", ".join(term.is_a)),
        ("part of", ", ".join(term.part_of)),
        ("kinds", ", ".join(each.name for each in others if name in each.is_a)),
        ("parts", ", ".join(each.name for each in others if name in each.part_of)),
    ]
    lines = "".join(f"  {label}  {named}\n" for label, named in relations if named)
    return (
        f"{term.name}\n  means  {term.meaning}\n{lines}  added  {term.added.date().isoformat()}\n"
    )
