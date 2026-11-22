"""The terms under a term: each that is part of it or is a kind of it, and those under them."""

import pytest

from flowgraph.about import terms_under

# Each name over the names it is part of or a kind of.
HELD = {
    "gate": (),
    "lane": ("gate",),
    "check": ("lane",),
    "land": ("gate",),
    "story": ("check", "land"),
}


def test_the_terms_under_a_term_are_those_that_name_it_then_those_under_them() -> None:
    assert terms_under("gate", HELD) == ["lane", "land", "check", "story"]


def test_a_term_nothing_names_has_no_terms_under_it() -> None:
    assert terms_under("story", HELD) == []


def test_a_term_reached_by_two_ways_is_listed_once() -> None:
    assert terms_under("gate", HELD).count("story") == 1


@pytest.mark.parametrize("start", ["a", "b"])
def test_the_walk_ends_on_terms_that_close_a_cycle(start: str) -> None:
    held = {"a": ("b",), "b": ("a",)}
    assert terms_under(start, held) == ["b" if start == "a" else "a"]
