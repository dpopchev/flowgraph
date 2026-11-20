"""Where locate finds the record: `.fgraph/` before `fgraph/` in a directory, or the path given."""

from collections.abc import Collection
from pathlib import Path

import pytest

from flowgraph.record import NAMES, Found, Given, GivenMissing, IsDir, NotFound, locate

pytestmark = pytest.mark.model

CWD = Path("/work")


def dirs(*names: str) -> IsDir:
    """A fake is_dir: true only for the named entries of CWD and the absolute paths given."""
    existing: Collection[Path] = {CWD / name for name in names}
    return lambda path: path in existing


def test_finds_the_dot_directory() -> None:
    assert locate(CWD, None, dirs(".fgraph")) == Found(CWD / ".fgraph")


def test_prefers_the_dot_directory_when_both_exist() -> None:
    assert locate(CWD, None, dirs(".fgraph", "fgraph")) == Found(CWD / ".fgraph")


def test_falls_back_to_the_plain_directory() -> None:
    assert locate(CWD, None, dirs("fgraph")) == Found(CWD / "fgraph")


def test_reports_both_names_tried_when_neither_exists() -> None:
    assert locate(CWD, None, dirs()) == NotFound(CWD, NAMES)


def test_takes_the_given_directory_without_searching() -> None:
    given = CWD / "elsewhere"
    assert locate(CWD, given, dirs(".fgraph", "elsewhere")) == Given(given)


def test_reports_a_given_path_that_is_no_directory_without_falling_back() -> None:
    given = CWD / "missing"
    assert locate(CWD, given, dirs(".fgraph")) == GivenMissing(given)
