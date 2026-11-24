"""The deviation of an amend: one knowledge line of that kind, none when no text is given."""

import argparse
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import EmptyPartError
from flowgraph.knowledge import DEVIATION, KnowledgeLine
from flowgraph.parser.stated import deviation_given

pytestmark = pytest.mark.model

NOW = datetime(2026, 1, 1, 12, 30, 15, 500, tzinfo=UTC)


def never() -> Never:
    """A clock that an amend given no deviation never reads."""
    raise AssertionError("an amend given no deviation reads no clock")


def test_no_text_gives_no_line_and_reads_no_clock() -> None:
    assert deviation_given(argparse.Namespace(deviation=None), never) is None


def test_a_text_gives_a_deviation_noted_to_the_second() -> None:
    line = deviation_given(argparse.Namespace(deviation="the then is narrowed"), lambda: NOW)
    assert line == KnowledgeLine(DEVIATION, "the then is narrowed", NOW.replace(microsecond=0))


def test_a_blank_text_is_refused() -> None:
    with pytest.raises(EmptyPartError, match=r"^text is empty$"):
        deviation_given(argparse.Namespace(deviation=" "), lambda: NOW)
