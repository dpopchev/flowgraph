"""The state of a Feature: in Backlog or started, the move between them, and its file."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.feature import (
    FeatureFileError,
    StartedFeature,
    make_feature,
    read_feature,
    started_feature,
    write_feature,
)
from flowgraph.parent import make_feature_id
from flowgraph.task import StartedAlreadyError

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 8, 0, 0, 500, tzinfo=UTC)
ONE = make_feature_id(1)
FEATURE = make_feature(ONE, "a title", ["a criterion", "another"], "why", CREATED)
STARTED = started_feature(FEATURE, ON)
FILE = Path("items") / "F-0001.toml"
WRITTEN_BEFORE = (
    'id = "F-0001"\n'
    'title = "a title"\n'
    'description = "why"\n'
    "created = 2026-01-01 12:30:15+00:00\n"
    'criteria = ["a criterion", "another"]\n'
)


def keep(tmp_path: Path, content: str) -> None:
    """Write the content as the file of F-0001 in the record at tmp_path."""
    (tmp_path / "items").mkdir()
    (tmp_path / FILE).write_text(content, "utf-8")


@pytest.mark.model
def test_a_feature_started_holds_its_started_time_to_the_second_and_what_it_held() -> None:
    assert started_feature(FEATURE, ON) == StartedFeature(
        ONE, "a title", "why", ("a criterion", "another"), CREATED, ON.replace(microsecond=0)
    )


@pytest.mark.model
def test_a_started_feature_started_once_more_is_refused() -> None:
    with pytest.raises(StartedAlreadyError, match=r"^F-0001 is started already$"):
        started_feature(STARTED, ON)


@pytest.mark.edge
def test_a_started_feature_is_written_with_its_state_line_and_its_started_time(
    tmp_path: Path,
) -> None:
    write_feature(tmp_path, STARTED)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8")) == {
        "id": "F-0001",
        "state": "started",
        "title": "a title",
        "description": "why",
        "created": CREATED,
        "started": ON.replace(microsecond=0),
        "criteria": ["a criterion", "another"],
    }


@pytest.mark.edge
def test_a_started_feature_reads_back_whole(tmp_path: Path) -> None:
    write_feature(tmp_path, STARTED)
    assert read_feature(tmp_path, ONE) == STARTED


@pytest.mark.edge
def test_a_file_without_a_state_line_reads_as_a_feature_in_backlog(tmp_path: Path) -> None:
    keep(tmp_path, WRITTEN_BEFORE)
    assert read_feature(tmp_path, ONE) == FEATURE


@pytest.mark.edge
@pytest.mark.parametrize(
    "lines",
    [
        'state = "backlog"\nstarted = 2026-01-02 08:00:00+00:00\n',
        "started = 2026-01-02 08:00:00+00:00\n",
        'state = "started"\n',
        'state = "completed"\n',
    ],
    ids=[
        "in-backlog-with-a-started-time",
        "no-state-line-with-a-started-time",
        "started-without-its-time",
        "a-state-a-feature-has-not",
    ],
)
def test_a_file_whose_state_line_and_times_disagree_is_refused_naming_it(
    lines: str, tmp_path: Path
) -> None:
    keep(tmp_path, f"{lines}{WRITTEN_BEFORE}")
    with pytest.raises(FeatureFileError, match=r"F-0001.toml holds no Feature: "):
        read_feature(tmp_path, ONE)
