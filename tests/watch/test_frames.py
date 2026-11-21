"""The frames of watch: a text read anew and written every interval, until its pace ends it."""

from collections.abc import Iterator

import pytest

from flowgraph.watch import CLEAR, Pace, framed, watch

pytestmark = pytest.mark.view


def texts() -> Iterator[str]:
    """The text of each frame in turn: `frame 1`, `frame 2` and so on, without an end."""
    number = 0
    while True:
        number += 1
        yield f"frame {number}\n"


def watched(pace: Pace) -> list[str]:
    """Everything a watch at that pace does in order: each frame written and each wait asked."""
    done: list[str] = []
    read = texts()
    watch(lambda: next(read), done.append, lambda seconds: done.append(f"wait {seconds}"), pace)
    return done


def interrupt(_: float) -> None:
    """The wait the developer ends with Ctrl-C."""
    raise KeyboardInterrupt


def test_a_frame_is_read_anew_and_written_after_each_wait() -> None:
    assert watched(Pace(5, 3)) == ["frame 1\n", "wait 5", "frame 2\n", "wait 5", "frame 3\n"]


def test_the_wait_between_two_frames_is_the_seconds_of_the_pace() -> None:
    assert watched(Pace(0.5, 2))[1] == "wait 0.5"


def test_no_wait_follows_the_last_frame() -> None:
    assert watched(Pace(5, 1)) == ["frame 1\n"]


def test_an_interrupt_of_the_wait_ends_a_watch_without_a_count() -> None:
    written: list[str] = []
    watch(lambda: "a frame\n", written.append, interrupt, Pace(5, None))
    assert written == ["a frame\n"]


def test_a_frame_on_a_terminal_replaces_the_one_before_it() -> None:
    assert framed("a line\n", 80) == f"{CLEAR}a line\n"


def test_a_frame_on_a_terminal_has_each_line_cut_to_its_width() -> None:
    assert framed("ab\n0123456789\n", 8) == f"{CLEAR}ab\n01234...\n"


def test_a_frame_written_to_no_terminal_is_the_text_whole() -> None:
    assert framed("0123456789\n", None) == "0123456789\n"
