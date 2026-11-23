"""The ids of the parsed arguments, read in every spelling that names them."""

import argparse
from typing import Any

from flowgraph.item.id import id_spelled

# The arguments that hold an id: a text, or for a relation that repeats, a list of texts.
ID_ARGUMENTS = ("id", "before", "parent", "depends_on", "filed_during", "amends", "superseded_by")


def _read(value: Any) -> Any:
    """The text or the list of texts with each spelling of an id replaced by its canonical id."""
    if isinstance(value, str):
        return id_spelled(value)
    if isinstance(value, list):
        return [_read(each) for each in value]
    return value


def ids_read(args: argparse.Namespace) -> argparse.Namespace:
    """The arguments with each id they hold written in its canonical form.

    The arguments are not changed. A text that is no spelling of an id, a term name, a path or
    `none`, stays as typed, and so do the options that name a term or a party.
    """
    return argparse.Namespace(
        **{
            name: _read(value) if name in ID_ARGUMENTS else value
            for name, value in vars(args).items()
        }
    )
