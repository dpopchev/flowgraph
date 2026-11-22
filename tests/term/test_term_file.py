"""The file of a term: `terms/gate.toml` in the record, written checked and read back whole."""

import re
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph import term as term_module
from flowgraph.term import (
    TermFileError,
    TermMismatchError,
    TermNotFoundError,
    make_term,
    read_term,
    read_term_names,
    relate,
    term_file,
    write_term,
)

pytestmark = pytest.mark.edge

ADDED = datetime(2026, 1, 1, tzinfo=UTC)
TERM = make_term("gate", "a check every deliverable passes", ADDED)
FILE = Path("terms") / "gate.toml"


def test_a_term_is_kept_as_one_file_named_by_its_name(tmp_path: Path) -> None:
    assert term_file(tmp_path, "gate") == tmp_path / FILE


def test_a_term_is_written_as_its_name_its_meaning_and_its_time(tmp_path: Path) -> None:
    write_term(tmp_path, TERM)
    written = tomllib.loads((tmp_path / FILE).read_text("utf-8"))
    assert written == {"name": "gate", "meaning": TERM.meaning, "added": ADDED}


def test_a_term_reads_back_whole(tmp_path: Path) -> None:
    write_term(tmp_path, TERM)
    assert read_term(tmp_path, "gate") == TERM


def test_a_term_the_record_holds_none_of_is_refused_by_name(tmp_path: Path) -> None:
    with pytest.raises(TermNotFoundError, match=re.escape("no term 'gate' in the record")):
        read_term(tmp_path, "gate")


def test_the_names_of_the_terms_are_those_of_their_files(tmp_path: Path) -> None:
    write_term(tmp_path, TERM)
    write_term(tmp_path, make_term("work-item", "a unit of work", ADDED))
    assert sorted(read_term_names(tmp_path)) == ["gate", "work-item"]


def test_a_record_without_terms_holds_no_name(tmp_path: Path) -> None:
    assert read_term_names(tmp_path) == []


@pytest.mark.parametrize(
    ("content", "why"),
    [
        ("not a term", "holds no term"),
        ('name = "gate"\nadded = 2026-01-01T00:00:00Z\n', "holds no term"),
        ('name = "gate"\nmeaning = " "\nadded = 2026-01-01T00:00:00Z\n', "holds no term: meaning"),
        ('name = "Gate"\nmeaning = "m"\nadded = 2026-01-01T00:00:00Z\n', "holds no term: 'Gate'"),
        ('name = "other"\nmeaning = "m"\nadded = 2026-01-01T00:00:00Z\n', "holds no term: it is"),
    ],
    ids=["no-toml", "no-meaning", "blank-meaning", "bad-name", "name-of-another-file"],
)
def test_a_file_that_holds_no_term_is_refused_naming_it(
    tmp_path: Path, content: str, why: str
) -> None:
    (tmp_path / "terms").mkdir()
    (tmp_path / FILE).write_text(content, encoding="utf-8")
    with pytest.raises(TermFileError, match=rf"^{tmp_path / FILE} {why}"):
        read_term(tmp_path, "gate")


class TestAWriteThatReadsBackDifferent:
    @pytest.fixture
    def failed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
        """The file and the message of a write whose read-back holds another meaning."""
        path = tmp_path / FILE
        path.parent.mkdir()
        path.write_text("previous", encoding="utf-8")
        other = {"name": "gate", "meaning": "other", "added": ADDED}
        monkeypatch.setattr(term_module.tomllib, "loads", lambda _: other)
        with pytest.raises(TermMismatchError) as error:
            write_term(tmp_path, TERM)
        return path, str(error.value)

    def test_keeps_the_previous_content(self, failed: tuple[Path, str]) -> None:
        assert failed[0].read_text(encoding="utf-8") == "previous"

    def test_names_the_path(self, failed: tuple[Path, str]) -> None:
        assert failed[1] == f"{failed[0]}: the term written reads back different"


def test_a_term_with_relations_is_written_with_them_and_reads_back_whole(tmp_path: Path) -> None:
    related = relate(relate(TERM, "part-of", "lane"), "is-a", "check")
    write_term(tmp_path, related)
    assert read_term(tmp_path, "gate") == related


def test_a_term_with_a_relation_is_written_with_the_names_of_its_kind(tmp_path: Path) -> None:
    write_term(tmp_path, relate(TERM, "part-of", "lane"))
    written = tomllib.loads((tmp_path / FILE).read_text("utf-8"))
    assert written["part_of"] == ["lane"]
