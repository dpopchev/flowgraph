"""The mark of a knowledge line: standing, open or none, read from a word and written as one."""

from datetime import UTC, datetime

import pytest

from flowgraph.knowledge import (
    FINDING,
    OPEN,
    STANDING,
    UNMARKED,
    Mark,
    MarkError,
    knowledge_row,
    make_knowledge_line,
    make_mark,
    mark_name,
    mark_text,
)

pytestmark = pytest.mark.model

NOTED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)


def test_a_line_made_with_no_mark_holds_no_mark() -> None:
    assert make_knowledge_line(FINDING, "a text", NOTED).mark == UNMARKED


def test_a_line_made_with_a_mark_holds_it() -> None:
    assert make_knowledge_line(FINDING, "a text", NOTED, mark=OPEN).mark == OPEN


@pytest.mark.parametrize(
    ("word", "mark"), [("standing", STANDING), ("open", OPEN), (None, UNMARKED)]
)
def test_a_word_names_its_mark(word: str | None, mark: Mark) -> None:
    assert make_mark(word) == mark


def test_a_word_that_is_no_mark_is_refused_by_name() -> None:
    with pytest.raises(MarkError, match=r"^'fact' is no mark: standing or open$"):
        make_mark("fact")


@pytest.mark.parametrize(("mark", "word"), [(STANDING, "standing"), (OPEN, "open"), (UNMARKED, "")])
def test_a_mark_is_written_as_its_word(mark: Mark, word: str) -> None:
    assert mark_name(mark) == word


def test_the_row_of_a_line_marked_open_holds_the_word_open() -> None:
    assert knowledge_row(make_knowledge_line(FINDING, "a text", NOTED, mark=OPEN)).mark == "open"


def test_the_text_of_the_open_mark_ends_a_line_after_two_spaces() -> None:
    assert mark_text("open") == "  (open)"


def test_the_text_of_no_mark_is_empty() -> None:
    assert mark_text("") == ""
