"""What every kind of work item states and proves: its Given / When / Then and its commit."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    """The one criterion of a work item: the initial state, the action and the expected state."""

    given: str
    when: str
    then: str


@dataclass(frozen=True)
class Commit:
    """The commit that holds the work of an item: its sha, 7 to 40 hex digits."""

    sha: str


class EmptyPartError(ValueError):
    """A part of an item that must say something is blank; `part` names it."""

    def __init__(self, part: str) -> None:
        super().__init__(f"{part} is empty")
        self.part = part


class CommitError(ValueError):
    """A text that is no commit sha."""


def said(part: str, text: str) -> str:
    """The text of the part, which must say something; raises EmptyPartError naming it."""
    if not text.strip():
        raise EmptyPartError(part)
    return text


def make_scenario(given: str, when: str, then: str) -> Scenario:
    """The criterion of a work item.

    Raises EmptyPartError naming the first part that is blank.
    """
    return Scenario(said("given", given), said("when", when), said("then", then))


def make_commit(text: str) -> Commit:
    """The commit of that sha.

    Raises CommitError when the text is not 7 to 40 lowercase hex digits.
    """
    if re.fullmatch(r"[0-9a-f]{7,40}", text) is None:
        raise CommitError(f"{text!r} is no commit: it is 7 to 40 hex digits")
    return Commit(text)
