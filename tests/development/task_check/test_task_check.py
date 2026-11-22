"""The check of a Task added: needed with the development on, refused with it off."""

from pathlib import Path

import pytest

from flowgraph.development.task_check import CheckError, check_task_checked

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


@pytest.mark.parametrize(("check", "development_on"), [("make test", True), (None, False)])
def test_a_task_added_the_way_the_development_asks_is_taken(
    check: str | None, development_on: bool
) -> None:
    assert check_task_checked(check, development_on, CONFIG) is None
