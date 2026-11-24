"""The line a landing prints of the criterion to run on main at its commit."""

from typing import assert_never

from flowgraph.criterion.model import Answer, Criterion, Defect, Hypothesis, Scenario

# The word a run line opens with, before the criterion to run.
RUN = "run: "


def _on_one_line(text: str) -> str:
    """The text with every run of blanks, its line breaks included, as one space."""
    return " ".join(text.split())


def run_line(criterion: Criterion) -> str:
    """The run line of the criterion, or the empty text for none.

    A Scenario is run as its When and its Then, a Bug as its expected; a hypothesis has none.
    """
    match criterion:
        case Scenario():
            return f"{RUN}{_on_one_line(criterion.when)} -> {_on_one_line(criterion.then)}\n"
        case Defect():
            return f"{RUN}{_on_one_line(criterion.expected)}\n"
        case Hypothesis() | Answer():
            return ""
        case _ as unreachable:
            assert_never(unreachable)
