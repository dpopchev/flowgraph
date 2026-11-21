"""What a work item states and proves: the criterion its kind takes, and its commit or none."""

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


@dataclass(frozen=True)
class Hypothesis:
    """The one criterion of a Spike: a question to answer."""

    question: str


@dataclass(frozen=True)
class Answer:
    """The criterion of a completed Spike: its hypothesis, and the decision that answers it."""

    question: str
    decision: str


# The criterion of a work item: the one its kind takes, a hypothesis answered once completed.
Criterion = Scenario | Defect | Hypothesis | Answer

# What a criterion of each form states, as a refusal words it.
STATES: Mapping[type[Criterion], str] = {
    Scenario: "a Given / When / Then",
    Defect: "what is observed and expected",
    Hypothesis: "a hypothesis",
    Answer: "a hypothesis and its decision",
}


@dataclass(frozen=True)
class Commit:
    """The commit that holds the work of an item: its sha, 7 to 40 hex digits."""

    sha: str


@dataclass(frozen=True)
class NoCommit:
    """An item completed without a commit: none is a value of its evidence, not a missing one."""


# The one value of no commit.
NO_COMMIT = NoCommit()

# What proves an item completed: the commit that holds its work, or none.
Evidence = Commit | NoCommit


class EmptyPartError(ValueError):
    """A part of an item that must say something is blank; `part` names it."""

    def __init__(self, part: str) -> None:
        super().__init__(f"{part} is empty")
        self.part = part


class CriterionError(ValueError):
    """A criterion of another form than the one a kind of work item takes."""


class DecisionError(ValueError):
    """A hypothesis completed without its decision, or a decision given where none answers."""


class CommitError(ValueError):
    """A text that is no commit sha."""


class CommitNeededError(ValueError):
    """An item completed without a commit while the development, whose evidence it is, is on."""


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


def make_hypothesis(question: str) -> Hypothesis:
    """The criterion of a Spike; raises EmptyPartError when the question is blank."""
    return Hypothesis(said("hypothesis", question))


def settled(criterion: Criterion, decision: str | None, named: str) -> Criterion:
    """The criterion as the completion of its work item leaves it, for the item of that name.

    A hypothesis is answered by the decision; every other criterion stays as it is. Raises
    DecisionError when a hypothesis is given no decision, or another criterion is given one,
    and EmptyPartError when the decision is blank.
    """
    match criterion:
        case Hypothesis():
            if decision is None:
                stated = STATES[Hypothesis]
                raise DecisionError(f"{named} is completed with its decision: it states {stated}")
            return Answer(criterion.question, said("decision", decision))
        case Scenario() | Defect() | Answer():
            if decision is not None:
                raise DecisionError(
                    f"{named} takes no decision: only a Spike is completed with one"
                )
            return criterion
        case _ as unreachable:
            assert_never(unreachable)


def criterion_parts(criterion: Criterion) -> dict[str, str]:
    """The parts of the criterion by name, in the order they are stated."""
    match criterion:
        case Scenario():
            return {"given": criterion.given, "when": criterion.when, "then": criterion.then}
        case Defect():
            return {"observed": criterion.observed, "expected": criterion.expected}
        case Hypothesis():
            return {"hypothesis": criterion.question}
        case Answer():
            return {"hypothesis": criterion.question, "decision": criterion.decision}
        case _ as unreachable:
            assert_never(unreachable)


def make_commit(text: str) -> Commit:
    """The commit of that sha.

    Raises CommitError when the text is not 7 to 40 lowercase hex digits.
    """
    if re.fullmatch(r"[0-9a-f]{7,40}", text) is None:
        raise CommitError(f"{text!r} is no commit: it is 7 to 40 hex digits")
    return Commit(text)


def evidence_text(evidence: Evidence) -> str:
    """The evidence as it is written: the sha of its commit, or nothing for none."""
    match evidence:
        case Commit():
            return evidence.sha
        case NoCommit():
            return ""
        case _ as unreachable:
            assert_never(unreachable)


def evidence_written(text: str) -> Evidence:
    """The evidence written as the text: none for nothing, else the commit of that sha.

    Raises CommitError when the text is neither.
    """
    return make_commit(text) if text else NO_COMMIT
