"""The lines a line of a Feature supersedes: kept on it in its file, read back whole."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.feature import (
    FeatureState,
    feature_detail,
    make_feature,
    note_feature,
    noted_feature,
    read_feature,
    write_feature,
)
from flowgraph.knowledge import DECISION, line_ref, make_knowledge_line
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_feature_id(1)
BARE = make_feature(ID, "a title", ["a criterion"], "", CREATED)
FIRST = make_knowledge_line(DECISION, "ship in two steps", ON)
SECOND = make_knowledge_line(DECISION, "ship in one", ON, supersedes=(line_ref("F-0001", 1),))
BOTH = noted_feature(noted_feature(BARE, FIRST), SECOND)


@pytest.fixture
def record(tmp_path: Path) -> Path:
    (tmp_path / "items").mkdir()
    return tmp_path


def first_table(record: Path) -> dict[str, object]:
    """The table of the first line of the file of the Feature, read with tomllib."""
    held = tomllib.loads((record / "items" / "F-0001.toml").read_text(encoding="utf-8"))
    return held["knowledge"][0]


def test_a_feature_with_a_line_that_supersedes_another_is_read_back_equal(record: Path) -> None:
    write_feature(record, BOTH)
    assert read_feature(record, ID) == BOTH


def test_the_detail_of_a_feature_holds_the_refs_the_line_supersedes() -> None:
    assert feature_detail(BOTH).knowledge[1].supersedes == ["F-0001#1"]


def test_the_table_of_the_first_line_is_left_as_written_when_a_later_supersedes_it(
    record: Path,
) -> None:
    write_feature(record, noted_feature(BARE, FIRST))
    before = first_table(record)
    write_feature(record, BOTH)
    assert first_table(record) == before


def test_the_table_of_a_line_that_supersedes_none_holds_no_key_supersedes(record: Path) -> None:
    write_feature(record, BOTH)
    assert "supersedes" not in first_table(record)


def test_a_note_that_supersedes_a_line_saves_a_feature_whose_last_line_holds_it() -> None:
    saved: list[FeatureState] = []
    note_feature(
        feature_id=ID,
        kind=DECISION,
        text="a text",
        load_feature=lambda _: BARE,
        save_feature=saved.append,
        now=lambda: ON,
        supersedes=("F-0001#1",),
    )
    assert saved[0].knowledge[-1].supersedes == ("F-0001#1",)
