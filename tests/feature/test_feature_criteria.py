"""The criteria of a Feature as rows: each met by a completed work item that realizes it."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import CriterionRow, criteria_rows
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
CRITERIA = ["a criterion", "another"]


def story(item: str, state: str, realizes: int | None = 1) -> WorkItemRow:
    """A work item under the Feature F-0001 in that state, realizing that criterion number."""
    return WorkItemRow(item, "a story", state, parent="F-0001", created=CREATED, realizes=realizes)


def test_two_criteria_and_no_row_give_two_criteria_none_realized_and_not_met() -> None:
    assert criteria_rows(CRITERIA, []) == [
        CriterionRow(1, "a criterion", [], False),
        CriterionRow(2, "another", [], False),
    ]


def test_a_completed_row_realizing_the_first_criterion_meets_it_and_leaves_the_second() -> None:
    assert criteria_rows(CRITERIA, [story("S-0001", "completed")]) == [
        CriterionRow(1, "a criterion", ["S-0001"], True),
        CriterionRow(2, "another", [], False),
    ]


@pytest.mark.parametrize("state", ["backlog", "started", "blocked"])
def test_a_row_not_completed_realizing_the_first_criterion_is_listed_and_not_met(
    state: str,
) -> None:
    assert criteria_rows(CRITERIA, [story("S-0001", state)]) == [
        CriterionRow(1, "a criterion", ["S-0001"], False),
        CriterionRow(2, "another", [], False),
    ]


def test_a_removed_row_realizing_the_first_criterion_is_not_listed() -> None:
    assert criteria_rows(CRITERIA, [story("S-0001", "removed")]) == [
        CriterionRow(1, "a criterion", [], False),
        CriterionRow(2, "another", [], False),
    ]


def test_a_completed_and_a_started_row_on_the_first_criterion_are_listed_and_it_is_met() -> None:
    assert criteria_rows(CRITERIA, [story("S-0001", "completed"), story("S-0002", "started")]) == [
        CriterionRow(1, "a criterion", ["S-0001", "S-0002"], True),
        CriterionRow(2, "another", [], False),
    ]


def test_the_ids_of_a_criterion_keep_the_order_of_the_rows_given() -> None:
    assert criteria_rows(CRITERIA, [story("S-0002", "started"), story("S-0001", "completed")]) == [
        CriterionRow(1, "a criterion", ["S-0002", "S-0001"], True),
        CriterionRow(2, "another", [], False),
    ]


def test_a_row_that_realizes_no_number_is_on_no_criterion() -> None:
    assert criteria_rows(CRITERIA, [story("S-0001", "completed", realizes=None)]) == [
        CriterionRow(1, "a criterion", [], False),
        CriterionRow(2, "another", [], False),
    ]


def test_a_row_that_realizes_a_number_the_criteria_do_not_have_is_on_no_criterion() -> None:
    assert criteria_rows(CRITERIA, [story("S-0001", "completed", realizes=3)]) == [
        CriterionRow(1, "a criterion", [], False),
        CriterionRow(2, "another", [], False),
    ]
