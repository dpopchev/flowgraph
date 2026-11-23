"""The complexity of a work item: low, medium or high, kept for whoever hands it to an agent."""

from typing import Literal, get_args

# How hard a work item is, as its author judged it.
Complexity = Literal["low", "medium", "high"]

# The complexities, in order.
COMPLEXITIES: tuple[Complexity, ...] = get_args(Complexity)


class ComplexityError(ValueError):
    """A word that is none of the complexities; the message names them."""


def make_complexity(word: str) -> Complexity:
    """The complexity the word names; raises ComplexityError naming the three when it is none."""
    for each in COMPLEXITIES:
        if word == each:
            return each
    raise ComplexityError(f"--complexity {word!r} is none of {', '.join(COMPLEXITIES)}")
