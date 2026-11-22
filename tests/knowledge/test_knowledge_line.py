"""A knowledge line: its kind, its text and the time it was noted, built by its constructor."""

from datetime import UTC, datetime

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.knowledge import FINDING, make_knowledge_line

pytestmark = pytest.mark.model

NOTED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)


def test_a_line_holds_its_kind() -> None:
    assert make_knowledge_line(FINDING, "the file holds it", NOTED).kind == FINDING


def test_a_line_holds_its_text() -> None:
    assert make_knowledge_line(FINDING, "the file holds it", NOTED).text == "the file holds it"


def test_the_time_noted_is_kept_to_the_second() -> None:
    line = make_knowledge_line(FINDING, "a text", NOTED.replace(microsecond=7))
    assert line.noted == NOTED


def test_a_blank_text_is_refused_by_name() -> None:
    with pytest.raises(EmptyPartError, match=r"^text is empty$"):
        make_knowledge_line(FINDING, " ", NOTED)
