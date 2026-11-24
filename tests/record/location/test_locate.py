"""Where locate finds the record: the path given, the folder a key names, `.fgraph/`, `fgraph/`."""

from collections.abc import Collection
from pathlib import Path

import pytest

from flowgraph.record import (
    NAMES,
    Found,
    Given,
    GivenMissing,
    IsDir,
    NamedMissing,
    NotFound,
    locate,
)

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


NAMED = CWD / ".dpopchev"


def never(directory: Path) -> Path | None:
    """A find_named that fails the test when it is asked."""
    raise AssertionError(f"find_named asked for {directory}")


def test_finds_the_folder_the_key_names() -> None:
    assert locate(CWD, None, dirs(".dpopchev"), lambda _: NAMED) == Found(NAMED)


def test_prefers_the_folder_the_key_names_to_the_fgraph_directories() -> None:
    assert locate(CWD, None, dirs(".dpopchev", ".fgraph", "fgraph"), lambda _: NAMED) == Found(
        NAMED
    )


def test_reports_a_folder_the_key_names_that_is_no_directory_though_the_dot_directory_exists() -> (
    None
):
    assert locate(CWD, None, dirs(".fgraph"), lambda _: NAMED) == NamedMissing(NAMED)


def test_finds_the_dot_directory_when_the_key_names_nothing() -> None:
    assert locate(CWD, None, dirs(".fgraph"), lambda _: None) == Found(CWD / ".fgraph")


def test_takes_the_given_directory_without_asking_the_key() -> None:
    given = CWD / "elsewhere"
    assert locate(CWD, given, dirs("elsewhere", ".dpopchev"), never) == Given(given)


def test_reports_a_given_path_that_is_no_directory_without_asking_the_key() -> None:
    given = CWD / "missing"
    assert locate(CWD, given, dirs(".dpopchev"), never) == GivenMissing(given)


def test_asks_the_key_for_the_directory_it_runs_in() -> None:
    asked: list[Path] = []

    def find_named(directory: Path) -> None:
        asked.append(directory)

    locate(CWD, None, dirs(".fgraph"), find_named)
    assert asked == [CWD]
