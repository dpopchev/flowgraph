"""The file of a Story: one TOML file per Story in `items/` of the record, read as rows."""

import re
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.story import (
    StoryFileError,
    StoryMismatchError,
    make_story,
    make_story_id,
    read_story_rows,
    story_row,
    write_story,
)
from flowgraph.work_item import file as story_file

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
STORY = make_story(make_story_id(1), "a title", SCENARIO, "", CREATED)


def test_a_story_is_written_as_its_own_file_in_items(tmp_path: Path) -> None:
    write_story(tmp_path, STORY)
    assert tomllib.loads((tmp_path / "items" / "S-0001.toml").read_text("utf-8")) == {
        "id": "S-0001",
        "state": "backlog",
        "title": "a title",
        "created": CREATED,
        "criterion": {"given": "a state", "when": "an action", "then": "another state"},
    }


def test_a_description_is_written_when_there_is_one(tmp_path: Path) -> None:
    write_story(tmp_path, make_story(make_story_id(1), "a title", SCENARIO, "why", CREATED))
    written = tomllib.loads((tmp_path / "items" / "S-0001.toml").read_text("utf-8"))
    assert written["description"] == "why"


def test_a_written_story_is_read_back_as_its_row(tmp_path: Path) -> None:
    write_story(tmp_path, STORY)
    assert read_story_rows(tmp_path) == [story_row(STORY)]


def test_the_rows_come_by_id(tmp_path: Path) -> None:
    for number in (3, 1, 2):
        write_story(tmp_path, make_story(make_story_id(number), "a title", SCENARIO, "", CREATED))
    assert [row.id for row in read_story_rows(tmp_path)] == ["S-0001", "S-0002", "S-0003"]


def test_a_record_with_no_items_directory_has_no_rows(tmp_path: Path) -> None:
    assert read_story_rows(tmp_path) == []


def test_a_file_of_another_kind_is_not_read_as_a_story(tmp_path: Path) -> None:
    write_story(tmp_path, STORY)
    (tmp_path / "items" / "B-0001.toml").write_text('id = "B-0001"\n', encoding="utf-8")
    assert read_story_rows(tmp_path) == [story_row(STORY)]


def test_an_st_file_of_an_older_record_is_not_read_as_a_story(tmp_path: Path) -> None:
    write_story(tmp_path, STORY)
    (tmp_path / "items" / "ST-0001.toml").write_text('id = "ST-0001"\n', encoding="utf-8")
    assert read_story_rows(tmp_path) == [story_row(STORY)]


@pytest.mark.parametrize("text", ['id = "S-0001"\n', "no toml at all"], ids=["partial", "no-toml"])
def test_a_file_that_is_no_story_is_refused_by_its_path(tmp_path: Path, text: str) -> None:
    path = tmp_path / "items" / "S-0001.toml"
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    with pytest.raises(StoryFileError, match=re.escape(str(path))):
        read_story_rows(tmp_path)


class TestAWriteThatReadsBackDifferent:
    @pytest.fixture
    def failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
        """The path of a Story written over a previous file, and the message of its failure."""
        path = tmp_path / "items" / "S-0001.toml"
        path.parent.mkdir()
        path.write_text("previous", encoding="utf-8")
        another = {
            "id": "S-0001",
            "state": "backlog",
            "title": "another title",
            "created": CREATED,
            "criterion": {"given": "a state", "when": "an action", "then": "another state"},
        }
        monkeypatch.setattr(story_file.tomllib, "loads", lambda _: another)
        with pytest.raises(StoryMismatchError) as error:
            write_story(tmp_path, STORY)
        return path, str(error.value)

    def test_keeps_the_previous_content(self, failed: tuple[Path, str]) -> None:
        assert failed[0].read_text(encoding="utf-8") == "previous"

    def test_names_the_path(self, failed: tuple[Path, str]) -> None:
        assert str(failed[0]) in failed[1]

    def test_leaves_nothing_beside_the_file(self, failed: tuple[Path, str]) -> None:
        assert [path.name for path in failed[0].parent.iterdir()] == ["S-0001.toml"]
