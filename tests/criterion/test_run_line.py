"""The run line of a criterion: the When and the Then, or the expected of a Bug, on one line."""

import pytest

from flowgraph.criterion import (
    Answer,
    Criterion,
    make_defect,
    make_hypothesis,
    make_scenario,
    run_line,
)

pytestmark = pytest.mark.model


def test_a_scenario_is_run_as_its_when_and_then() -> None:
    assert run_line(make_scenario("a state", "an action", "another")) == (
        "run: an action -> another\n"
    )


def test_a_defect_is_run_as_its_expected() -> None:
    assert run_line(make_defect("it fails", "it works")) == "run: it works\n"


def test_a_hypothesis_has_no_run_line() -> None:
    assert run_line(make_hypothesis("a question")) == ""


def test_an_answered_hypothesis_has_no_run_line() -> None:
    assert run_line(Answer("a question", "a decision", "yes")) == ""


def test_a_when_over_two_lines_is_printed_on_one_line() -> None:
    assert run_line(make_scenario("a state", "an action\n  over two lines", "another")) == (
        "run: an action over two lines -> another\n"
    )


def test_a_then_with_a_tab_and_a_trailing_newline_is_printed_on_one_line() -> None:
    assert run_line(make_scenario("a state", "an action", "another\t\n")) == (
        "run: an action -> another\n"
    )


@pytest.mark.parametrize(
    "criterion",
    [make_scenario("a state", "an action", "another"), make_defect("it fails", "it works")],
)
def test_a_run_line_ends_with_exactly_one_newline(criterion: Criterion) -> None:
    assert run_line(criterion).count("\n") == 1
