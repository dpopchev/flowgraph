"""A term named by its name: its add, its list and its view.

Each runs on the store of a record, as the commands of a work item do (`flowgraph.item`).
"""

from flowgraph.item import MESSAGE, Written
from flowgraph.record import Now
from flowgraph.store import Store
from flowgraph.term import make_term


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
    return f"{term.name}\n  means  {term.meaning}\n  added  {term.added.date().isoformat()}\n"
