"""The criteria of a Feature in its text: met k of n once a work item under it names one."""

from datetime import UTC, datetime

import pytest

from flowgraph.feature import FeatureDetail
from flowgraph.status import feature_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)
DETAIL = FeatureDetail("F-0001", "a feature title", "", ["a criterion", "another"])


def row(item: str, state: str, realizes: int | None = None) -> WorkItemRow:
    """A work item under F-0001 in that state, realizing that criterion number, none for none."""
    return WorkItemRow(item, "a story", state, parent="F-0001", created=CREATED, realizes=realizes)


def criteria_lines(rows: list[WorkItemRow]) -> list[str]:
    """The lines of the text of F-0001 from its Criteria heading up to its Work items heading."""
    shown = feature_text(DETAIL, rows, "InProgress").splitlines()
    first = next(index for index, line in enumerate(shown) if line.startswith("Criteria ("))
    last = next(index for index, line in enumerate(shown) if line.startswith("Work items ("))
    return shown[first:last]


def test_no_row_naming_a_criterion_lists_the_criteria_as_before() -> None:
    assert criteria_lines([row("S-0001", "backlog")]) == [
        "Criteria (2)",
        "  a criterion",
        "  another",
    ]


def test_a_completed_row_on_the_first_criterion_meets_it() -> None:
    assert criteria_lines([row("S-0001", "completed", 1)]) == [
        "Criteria (2), met 1 of 2",
        "  1  met      a criterion  S-0001",
        "  2  not met  another",
    ]


def test_a_row_in_backlog_on_the_second_criterion_is_listed_on_its_line_not_met() -> None:
    assert criteria_lines([row("S-0001", "backlog", 2)]) == [
        "Criteria (2), met 0 of 2",
        "  1  not met  a criterion",
        "  2  not met  another  S-0001",
    ]


def test_two_rows_on_the_first_criterion_one_completed_list_both_and_meet_it() -> None:
    assert criteria_lines([row("S-0001", "completed", 1), row("S-0002", "started", 1)]) == [
        "Criteria (2), met 1 of 2",
        "  1  met      a criterion  S-0001, S-0002",
        "  2  not met  another",
    ]


def test_only_a_removed_row_naming_a_criterion_lists_the_criteria_as_before() -> None:
    assert criteria_lines([row("S-0001", "removed", 1)]) == [
        "Criteria (2)",
        "  a criterion",
        "  another",
    ]


def test_both_criteria_met_read_met_2_of_2() -> None:
    assert criteria_lines([row("S-0001", "completed", 1), row("S-0002", "completed", 2)]) == [
        "Criteria (2), met 2 of 2",
        "  1  met      a criterion  S-0001",
        "  2  met      another  S-0002",
    ]
