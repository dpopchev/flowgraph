"""A term of the project: a node of the record with no flow, its commands and the terms asked.

A term and its file are named here. Its commands and the terms a command names run on the store
of a record, which reads a term through this package, so each is imported from its own module:
item and about.
"""

from flowgraph.term.model import (
    KINDS,
    Term,
    TermError,
    TermFileError,
    TermMismatchError,
    TermNotFoundError,
    is_term_name,
    make_term,
    read_term,
    read_term_names,
    relate,
    term_file,
    write_term,
)

__all__ = [
    "KINDS",
    "Term",
    "TermError",
    "TermFileError",
    "TermMismatchError",
    "TermNotFoundError",
    "is_term_name",
    "make_term",
    "read_term",
    "read_term_names",
    "relate",
    "term_file",
    "write_term",
]
