"""The terms an item or a line is about, as a command names them: checked against the record.

A term is named by a command that adds, amends or notes an item, or narrows a list. A term the
record holds none of is refused with how to add it, and nothing is written.
"""

from collections.abc import Sequence

from flowgraph.parent import NONE
from flowgraph.record.store import Store
from flowgraph.term.model import TermError


def term_asked(name: str, store: Store) -> str:
    """The name of a term the record holds.

    Raises TermError naming `fgraph add term` when the record holds no term of that name.
    """
    if name not in store.terms.find_term_names():
        raise TermError(f"no term {name!r} in the record: add it with fgraph add term")
    return name


def about_asked(names: Sequence[str] | None, store: Store) -> tuple[str, ...] | None:
    """The terms a command asks an item or a line to be about, each once, in order.

    None when it names none.

    `none` alone is no term at all: an empty tuple, which an amend takes as every term away.
    Raises TermError when `none` is given with others and when the record holds no term of a
    name; nothing is written.
    """
    if names is None:
        return None
    if NONE in names:
        if len(names) > 1:
            raise TermError(f"{NONE} stands alone: it takes every term away")
        return ()
    return tuple(dict.fromkeys(term_asked(name, store) for name in names))
