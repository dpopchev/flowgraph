"""The text of status on a terminal: a line cut to its width, the commit kept before the title."""

from datetime import UTC, datetime

import pytest

from flowgraph.text import cut_lines, status_text
from flowgraph.work_item import WorkItemRow

pytestmark = pytest.mark.view

CREATED = datetime(2026, 1, 1, tzinfo=UTC)


def test_a_line_longer_than_the_width_is_cut_to_it_and_ends_with_the_mark() -> None:
    assert cut_lines("0123456789\n", 8) == "01234...\n"


def test_a_line_as_long_as_the_width_is_whole() -> None:
    assert cut_lines("01234567\n", 8) == "01234567\n"


def test_each_line_is_cut_on_its_own() -> None:
    assert cut_lines("ab\n0123456789\ncd\n", 8) == "ab\n01234...\ncd\n"


def test_every_line_is_whole_without_a_width() -> None:
    assert cut_lines("0123456789\n", None) == "0123456789\n"


def test_a_completed_work_item_is_listed_with_its_commit_before_its_title() -> None:
    rows = [WorkItemRow("ST-0001", "a title", "completed", "abc1234", created=CREATED)]
    assert status_text(rows).splitlines()[3] == "  ST-0001  abc1234  a title"
