"""The check of a Task added: needed with the development on, refused with it off."""

from pathlib import Path

import pytest

from flowgraph.development.task_check import (
    CheckError,
    check_task_amended,
    check_task_checked,
)

pytestmark = pytest.mark.model

CONFIG = Path("/src/project/.fgraph/config.toml")


def test_no_check_with_the_development_on_is_refused_naming_the_flag() -> None:
    with pytest.raises(CheckError, match=r"^the development is on, .* with --check COMMAND$"):
        check_task_checked(None, True, CONFIG)


def test_a_check_with_the_development_off_is_refused_naming_the_key() -> None:
    with pytest.raises(
        CheckError,
        match=r" -- set development\.enabled = true in /src/project/\.fgraph/config\.toml$",
    ):
        check_task_checked("make test", False, CONFIG)


def test_an_amend_giving_a_check_with_the_development_off_is_refused_with_the_whole_line() -> None:
    with pytest.raises(
        CheckError,
        match=(
            r"^a Task takes no --check: the development is off"
            r" -- set development\.enabled = true in /src/project/\.fgraph/config\.toml$"
        ),
    ):
        check_task_amended("make lint", False, CONFIG)


@pytest.mark.parametrize(
    ("check", "development_on"),
    [(None, True), (None, False), ("make lint", True)],
    ids=["none-on", "none-off", "given-on"],
)
def test_an_amend_that_names_no_check_or_names_one_with_the_development_on_is_taken(
    check: str | None, development_on: bool
) -> None:
    assert check_task_amended(check, development_on, CONFIG) is None


@pytest.mark.parametrize(("check", "development_on"), [("make test", True), (None, False)])
def test_a_task_added_the_way_the_development_asks_is_taken(
    check: str | None, development_on: bool
) -> None:
    assert check_task_checked(check, development_on, CONFIG) is None
