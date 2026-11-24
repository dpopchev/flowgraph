"""What the arguments of a command state of a work item: the criterion of an add, the decision of
a complete or a land, and the deviation of an amend."""

import argparse

from flowgraph.criterion import (
    Criterion,
    Decision,
    make_decision,
    make_defect,
    make_hypothesis,
    make_scenario,
)
from flowgraph.knowledge import DEVIATION, KnowledgeLine, make_knowledge_line
from flowgraph.record import Now


def criterion_added(args: argparse.Namespace) -> Criterion:
    """The criterion the arguments of an add state, in the form the kind added takes.

    Raises EmptyPartError naming the first part that is blank.
    """
    match args.kind:
        case "bug":
            return make_defect(args.observed, args.expected)
        case "spike":
            return make_hypothesis(args.hypothesis)
        case _:
            return make_scenario(args.given, args.when, args.then)


def decision_given(args: argparse.Namespace) -> Decision | None:
    """The decision the arguments of a complete or a land give, none when they give none.

    Raises DecisionError when an answer is given without its decision.
    """
    return make_decision(args.decision, args.answer)


def deviation_given(args: argparse.Namespace, now: Now) -> KnowledgeLine | None:
    """The deviation the arguments of an amend give, none when they give none.

    It is a line of kind deviation about no term, governing no file; the clock is read only when
    a text is given. Raises EmptyPartError when the text is blank.
    """
    if args.deviation is None:
        return None
    return make_knowledge_line(DEVIATION, args.deviation, now())
