"""The answer of the closing of a completed work item: yes or no, with what the run printed and
when.

It is a fact of the completed work item, never a knowledge line. A no moves nothing backwards:
the work item stays completed, and the no files a Bug that amends it.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from flowgraph.criterion import said

# The answers a closing is kept with.
Verdict = Literal["yes", "no"]

# What the refusals of a verify say it takes.
TAKES = "fgraph verify takes a completed Story, Bug or Upkeep"


@dataclass(frozen=True)
class Verification:
    """The answer of a closing, the text the run of the criterion printed and the time of it."""

    answer: Verdict
    text: str
    on: datetime


class NotVerifiableError(ValueError):
    """A work item to verify that is not completed, or a Spike; the message names what it takes."""


class VerifiedAlreadyError(ValueError):
    """A work item to verify that holds the answer of its closing already."""


def make_verification(answer: Verdict, text: str, on: datetime) -> Verification:
    """The answer of a closing with the text the run printed, the time kept to the second.

    Raises EmptyPartError naming the text when it is blank.
    """
    return Verification(answer, said("text", text), on.replace(microsecond=0))
