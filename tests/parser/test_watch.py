"""The arguments of watch: the seconds between two frames, the frames it ends after, every item."""

import pytest

from flowgraph.parser import build_command_line

pytestmark = pytest.mark.view

PARSER = build_command_line().parser


@pytest.mark.parametrize(
    ("argv", "seconds"),
    [(["watch"], 5), (["watch", "-n", "2"], 2), (["watch", "-n", "0.5"], 0.5)],
    ids=["five-by-default", "given", "a-part-of-a-second"],
)
def test_watch_waits_the_seconds_given_with_n_between_two_frames(
    argv: list[str], seconds: float
) -> None:
    assert PARSER.parse_args(argv).seconds == seconds


@pytest.mark.parametrize(
    ("argv", "count"),
    [(["watch"], None), (["watch", "--count", "3"], 3)],
    ids=["without-an-end", "given"],
)
def test_watch_ends_after_the_frames_given_with_count(argv: list[str], count: int | None) -> None:
    assert PARSER.parse_args(argv).count == count


@pytest.mark.parametrize(
    ("argv", "every"),
    [(["watch"], False), (["watch", "--all"], True)],
    ids=["the-top", "every-one"],
)
def test_watch_asks_for_every_item_with_all_alone(argv: list[str], every: bool) -> None:
    assert PARSER.parse_args(argv).all is every


@pytest.mark.parametrize(
    "argv",
    [["watch", "-n", "soon"], ["watch", "--count", "1.5"], ["watch", "--count", "many"]],
    ids=["seconds-no-number", "count-no-whole-number", "count-no-number"],
)
def test_watch_given_no_number_exits_with_two(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as refused:
        PARSER.parse_args(argv)
    assert refused.value.code == 2
