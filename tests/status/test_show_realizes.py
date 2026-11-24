"""The text of fgraph show for a work item that realizes a criterion of its Feature."""

import pytest

from flowgraph.status import show_text
from flowgraph.work_item import WorkItemDetail

pytestmark = pytest.mark.view


def detail(realizes: int | None, realized: str) -> WorkItemDetail:
    """The detail of S-0001 under F-0001 naming that criterion, its text as read."""
    return WorkItemDetail(
        "S-0001",
        "a title",
        "backlog",
        "",
        [],
        given="a state",
        when="an action",
        then="another",
        parent="F-0001",
        realizes=realizes,
        realized=realized,
    )


def test_show_lists_the_criterion_right_after_the_parent() -> None:
    shown = show_text(detail(2, "a second criterion"))
    assert shown.splitlines()[1:4] == [
        "  bucket       backlog",
        "  parent       F-0001",
        "  realizes     2  a second criterion",
    ]


def test_show_says_none_of_the_criteria_when_the_feature_has_no_such_one() -> None:
    shown = show_text(detail(3, ""))
    assert shown.splitlines()[3] == "  realizes     3  none of the criteria of F-0001"


def test_show_lists_no_realizes_line_for_a_work_item_naming_none() -> None:
    assert "realizes" not in show_text(detail(None, ""))
