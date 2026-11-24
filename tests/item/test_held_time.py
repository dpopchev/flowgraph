"""A HeldTime reads a time with its offset and refuses a day alone or a time with no offset."""

import re
import tomllib
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import BaseModel, ValidationError

from flowgraph.item import HeldTime, NoOffsetError

pytestmark = pytest.mark.edge

PLUS_TWO = timezone(timedelta(hours=2))
EXAMPLE = r"write it with one, as 2026-01-01 09:00:00\+00:00"


class Line(BaseModel):
    noted: HeldTime


class Held(BaseModel):
    created: HeldTime
    knowledge: list[Line] = []


def held(text: str) -> Held:
    return Held.model_validate(tomllib.loads(text))


@pytest.mark.parametrize(
    ("text", "time"),
    [
        ("created = 2026-10-11 09:00:00+00:00", datetime(2026, 10, 11, 9, tzinfo=UTC)),
        ("created = 2026-10-11T09:00:00Z", datetime(2026, 10, 11, 9, tzinfo=UTC)),
        ('created = "2026-10-11T09:00:00+00:00"', datetime(2026, 10, 11, 9, tzinfo=UTC)),
        ("created = 2026-10-11 09:00:00+02:00", datetime(2026, 10, 11, 9, tzinfo=PLUS_TWO)),
    ],
)
def test_a_time_with_an_offset_is_read_as_the_time_it_names(text: str, time: datetime) -> None:
    assert held(text).created == time


def test_a_time_with_an_offset_keeps_it() -> None:
    assert held("created = 2026-10-11 09:00:00+02:00").created.utcoffset() == timedelta(hours=2)


@pytest.mark.parametrize(
    ("text", "written"),
    [
        ("created = 2026-10-11", "2026-10-11"),
        ("created = 2026-10-11T09:00:00", "2026-10-11 09:00:00"),
        ('created = "2026-10-11"', "2026-10-11"),
        ('created = "2026-10-11T09:00:00"', "2026-10-11T09:00:00"),
    ],
)
def test_a_day_alone_or_a_time_with_no_offset_is_refused_in_one_line(
    text: str, written: str
) -> None:
    line = f"^created = {re.escape(written)} is a time with no offset: {EXAMPLE}$"
    with pytest.raises(NoOffsetError, match=line):
        held(text)


def test_a_time_in_a_list_of_tables_is_refused_naming_its_key() -> None:
    text = "created = 2026-10-11 09:00:00+00:00\n[[knowledge]]\nnoted = 2026-10-11\n"
    with pytest.raises(NoOffsetError, match=r"^noted = 2026-10-11 is a time with no offset"):
        held(text)


def test_a_text_that_is_no_time_is_refused_by_pydantic() -> None:
    with pytest.raises(ValidationError):
        held('created = "soon"')


def test_a_time_of_a_day_with_no_date_is_refused_by_pydantic() -> None:
    with pytest.raises(ValidationError):
        held("created = 09:00:00")


def test_no_offset_error_is_no_value_error() -> None:
    assert not issubclass(NoOffsetError, ValueError)
