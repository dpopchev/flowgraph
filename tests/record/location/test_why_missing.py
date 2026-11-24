"""The words after `fgraph: error:` for each way the record is missing."""

from pathlib import Path

import pytest

from flowgraph.record import NAMES, GivenMissing, NamedMissing, NotFound, why_missing

pytestmark = pytest.mark.view


def test_says_no_name_of_the_record_is_in_the_directory() -> None:
    assert why_missing(NotFound(Path("/work"), NAMES)) == (
        "no .fgraph/ or fgraph/ in /work -- run fgraph init, or pass --dir PATH"
    )


def test_says_the_directory_given_is_none() -> None:
    assert why_missing(GivenMissing(Path("/work/missing"))) == "--dir /work/missing is no directory"


def test_says_the_folder_the_key_names_is_none() -> None:
    assert why_missing(NamedMissing(Path("/work/.dpopchev"))) == (
        "git config fgraph.record names /work/.dpopchev, which is no directory"
        " -- run fgraph init, or name another with git config fgraph.record PATH"
    )
