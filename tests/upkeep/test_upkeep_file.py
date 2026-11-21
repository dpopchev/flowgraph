"""The file of an Upkeep: written as items/U-0001.toml, read back as rows and as detail."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_scenario
from flowgraph.upkeep import (
    UpkeepDetail,
    UpkeepFileError,
    UpkeepMismatchError,
    UpkeepNotFoundError,
    UpkeepRow,
    make_upkeep,
    make_upkeep_id,
    read_upkeep_detail,
    read_upkeep_rows,
    write_upkeep,
)
from flowgraph.upkeep import file as upkeep_file

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
SCENARIO = make_scenario("a behavior", "it runs", "it still holds")
UPKEEP = make_upkeep(make_upkeep_id(1), "a title", SCENARIO, "", CREATED)
FILE = Path("items") / "U-0001.toml"


def test_an_upkeep_is_written_as_its_one_file(tmp_path: Path) -> None:
    write_upkeep(tmp_path, UPKEEP)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8")) == {
        "id": "U-0001",
        "state": "backlog",
        "title": "a title",
        "created": CREATED,
        "criterion": {"given": "a behavior", "when": "it runs", "then": "it still holds"},
    }


def test_the_description_of_an_upkeep_is_written_when_there_is_one(tmp_path: Path) -> None:
    write_upkeep(tmp_path, make_upkeep(make_upkeep_id(1), "a title", SCENARIO, "why", CREATED))
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8"))["description"] == "why"


def test_the_upkeeps_of_a_record_are_read_as_rows_by_id(tmp_path: Path) -> None:
    write_upkeep(tmp_path, make_upkeep(make_upkeep_id(10), "a later title", SCENARIO, "", CREATED))
    write_upkeep(tmp_path, UPKEEP)
    assert read_upkeep_rows(tmp_path) == [
        UpkeepRow("U-0001", "a title", "backlog"),
        UpkeepRow("U-0010", "a later title", "backlog"),
    ]


def test_a_record_without_items_has_no_upkeep_rows(tmp_path: Path) -> None:
    assert read_upkeep_rows(tmp_path) == []


def test_a_file_of_another_kind_is_left_alone(tmp_path: Path) -> None:
    write_upkeep(tmp_path, UPKEEP)
    (tmp_path / "items" / "ST-0001.toml").write_text("not an upkeep", encoding="utf-8")
    assert [row.id for row in read_upkeep_rows(tmp_path)] == ["U-0001"]


def test_an_upkeep_is_read_as_detail(tmp_path: Path) -> None:
    write_upkeep(tmp_path, make_upkeep(make_upkeep_id(1), "a title", SCENARIO, "why", CREATED))
    assert read_upkeep_detail(tmp_path, make_upkeep_id(1)) == UpkeepDetail(
        id="U-0001",
        title="a title",
        state="backlog",
        description="why",
        given="a behavior",
        when="it runs",
        then="it still holds",
        tasks=[],
    )


def test_an_upkeep_the_record_does_not_hold_is_refused_by_its_id(tmp_path: Path) -> None:
    with pytest.raises(UpkeepNotFoundError, match=r"^no Upkeep U-0002 in the record$"):
        read_upkeep_detail(tmp_path, make_upkeep_id(2))


def test_a_file_that_holds_no_upkeep_is_refused_naming_it(tmp_path: Path) -> None:
    (tmp_path / "items").mkdir()
    (tmp_path / FILE).write_text('id = "U-0001"\n', encoding="utf-8")
    with pytest.raises(UpkeepFileError, match=r"U-0001\.toml holds no Upkeep"):
        read_upkeep_rows(tmp_path)


class TestAWriteThatReadsBackDifferent:
    @pytest.fixture
    def failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
        """The file and the message of a write whose read-back holds another title."""
        path = tmp_path / FILE
        path.parent.mkdir()
        path.write_text("previous", encoding="utf-8")
        another = {
            "id": "U-0001",
            "state": "backlog",
            "title": "another title",
            "created": CREATED,
            "criterion": {"given": "a behavior", "when": "it runs", "then": "it still holds"},
        }
        monkeypatch.setattr(upkeep_file.tomllib, "loads", lambda _: another)
        with pytest.raises(UpkeepMismatchError) as error:
            write_upkeep(tmp_path, UPKEEP)
        return path, str(error.value)

    def test_keeps_the_previous_content(self, failed: tuple[Path, str]) -> None:
        assert failed[0].read_text(encoding="utf-8") == "previous"

    def test_names_the_path(self, failed: tuple[Path, str]) -> None:
        assert str(failed[0]) in failed[1]
