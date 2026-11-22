"""What the arguments of a command state of a work item: the criterion of an add, the decision of
a complete or a land."""

import argparse

from flowgraph.criterion import (
    Criterion,
    Decision,
    make_decision,
    make_defect,
    make_hypothesis,
    make_scenario,
)


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
