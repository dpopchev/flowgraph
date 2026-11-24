"""The mark of a line of a Feature: kept in its file, read back whole, refused if wrong."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.feature import (
    FeatureFileError,
    FeatureState,
    feature_detail,
    make_feature,
    note_feature,
    noted_feature,
    read_feature,
    write_feature,
)
from flowgraph.knowledge import DECISION, OPEN, STANDING, Mark, make_knowledge_line
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_feature_id(1)
BARE = make_feature(ID, "a title", ["a criterion"], "", CREATED)


@pytest.fixture
def record(tmp_path: Path) -> Path:
    (tmp_path / "items").mkdir()
    return tmp_path


@pytest.mark.parametrize("mark", [STANDING, OPEN], ids=["standing", "open"])
def test_a_line_with_a_mark_is_read_back_equal(record: Path, mark: Mark) -> None:
    line = make_knowledge_line(DECISION, "a text", ON, mark=mark)
    write_feature(record, noted_feature(BARE, line))
    assert read_feature(record, ID).knowledge == (line,)


def test_the_detail_of_a_feature_holds_the_mark_of_the_line() -> None:
    line = make_knowledge_line(DECISION, "a text", ON, mark=OPEN)
    assert feature_detail(noted_feature(BARE, line)).knowledge[0].mark == "open"


def test_the_table_of_a_line_with_no_mark_holds_no_key_mark(record: Path) -> None:
    write_feature(record, noted_feature(BARE, make_knowledge_line(DECISION, "a text", ON)))
    held = tomllib.loads((record / "items" / "F-0001.toml").read_text(encoding="utf-8"))
    assert "mark" not in held["knowledge"][0]


def test_a_file_with_a_word_that_is_no_mark_is_refused_when_read(record: Path) -> None:
    line = make_knowledge_line(DECISION, "a text", ON, mark=OPEN)
    write_feature(record, noted_feature(BARE, line))
    path = record / "items" / "F-0001.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace('mark = "open"', 'mark = "fact"'),
        encoding="utf-8",
    )
    with pytest.raises(FeatureFileError, match=r"F-0001\.toml"):
        read_feature(record, ID)


def test_a_note_with_a_mark_saves_a_feature_whose_last_line_holds_it() -> None:
    saved: list[FeatureState] = []
    note_feature(
        feature_id=ID,
        kind=DECISION,
        text="a text",
        load_feature=lambda _: BARE,
        save_feature=saved.append,
        now=lambda: ON,
        mark=OPEN,
    )
    assert saved[0].knowledge[-1].mark == OPEN
