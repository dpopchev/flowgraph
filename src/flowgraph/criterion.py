"""What a work item states and proves: the criterion its kind takes, and its commit."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import assert_never


@dataclass(frozen=True)
class Scenario:
    """The one criterion of a work item: the initial state, the action and the expected state."""

    given: str
    when: str
    then: str


@dataclass(frozen=True)
class Defect:
    """The one criterion of a Bug: what is observed, and what is expected instead."""

    observed: str
    expected: str


# The criterion of a work item: the one its kind takes.
Criterion = Scenario | Defect

# What a criterion of each form states, as a refusal words it.
STATES: Mapping[type[Criterion], str] = {
    Scenario: "a Given / When / Then",
    Defect: "what is observed and expected",
}


@dataclass(frozen=True)
class Commit:
    """The commit that holds the work of an item: its sha, 7 to 40 hex digits."""

    sha: str


class EmptyPartError(ValueError):
    """A part of an item that must say something is blank; `part` names it."""

    def __init__(self, part: str) -> None:
        super().__init__(f"{part} is empty")
        self.part = part


class CriterionError(ValueError):
    """A criterion of another form than the one a kind of work item takes."""


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


def make_defect(observed: str, expected: str) -> Defect:
    """The criterion of a Bug.

    Raises EmptyPartError naming the first part that is blank.
    """
    return Defect(said("observed", observed), said("expected", expected))


def criterion_parts(criterion: Criterion) -> dict[str, str]:
    """The parts of the criterion by name, in the order they are stated."""
    match criterion:
        case Scenario():
            return {"given": criterion.given, "when": criterion.when, "then": criterion.then}
        case Defect():
            return {"observed": criterion.observed, "expected": criterion.expected}
        case _ as unreachable:
            assert_never(unreachable)


def make_commit(text: str) -> Commit:
    """The commit of that sha.

    Raises CommitError when the text is not 7 to 40 lowercase hex digits.
    """
    if re.fullmatch(r"[0-9a-f]{7,40}", text) is None:
        raise CommitError(f"{text!r} is no commit: it is 7 to 40 hex digits")
    return Commit(text)
