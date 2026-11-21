"""The pace of watch: the seconds between two frames and the frames it ends after, both positive."""

import math

import pytest

from flowgraph.watch import Pace, PaceError, make_pace

pytestmark = pytest.mark.model


def test_a_pace_holds_its_seconds_and_the_frames_it_ends_after() -> None:
    assert make_pace(2.5, 3) == Pace(2.5, 3)


def test_a_pace_without_a_count_ends_after_no_frame() -> None:
    assert make_pace(5, None) == Pace(5, None)


@pytest.mark.parametrize(
    ("seconds", "named"),
    [(0, "0"), (-1.5, "-1.5"), (math.nan, "nan"), (math.inf, "inf")],
    ids=["zero", "negative", "no-number", "endless"],
)
def test_seconds_that_are_no_positive_number_are_refused(seconds: float, named: str) -> None:
    with pytest.raises(PaceError, match=f"-n {named} is no positive number of seconds"):
        make_pace(seconds, None)


@pytest.mark.parametrize("count", [0, -2], ids=["zero", "negative"])
def test_a_count_that_is_no_positive_number_is_refused(count: int) -> None:
    with pytest.raises(PaceError, match=f"--count {count} is no positive number of frames"):
        make_pace(5, count)
