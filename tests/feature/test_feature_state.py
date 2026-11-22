"""The state of a Feature: in Backlog, started or completed, the moves between them, its file."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import NO_COMMIT, Evidence, make_commit
from flowgraph.feature import (
    CompletedFeature,
    FeatureFileError,
    StartedFeature,
    completed_feature,
    make_feature,
    read_feature,
    started_feature,
    write_feature,
)
from flowgraph.parent import make_feature_id
from flowgraph.task import CompletedAlreadyError, NotStartedError, StartedAlreadyError

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 8, 0, 0, 500, tzinfo=UTC)
DONE = datetime(2026, 1, 3, 9, 0, 0, 500, tzinfo=UTC)
COMMIT = make_commit("abc1234")
ONE = make_feature_id(1)
FEATURE = make_feature(ONE, "a title", ["a criterion", "another"], "why", CREATED)
STARTED = started_feature(FEATURE, ON)
COMPLETED = completed_feature(STARTED, DONE, COMMIT)
FILE = Path("items") / "F-0001.toml"
WRITTEN_BEFORE = (
    'id = "F-0001"\n'
    'title = "a title"\n'
    'description = "why"\n'
    "created = 2026-01-01 12:30:15+00:00\n"
    'criteria = ["a criterion", "another"]\n'
)
STARTED_ON = "started = 2026-01-02 08:00:00+00:00\n"
COMPLETED_ON = "completed = 2026-01-03 09:00:00+00:00\n"


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


@pytest.mark.model
@pytest.mark.parametrize("commit", [COMMIT, NO_COMMIT], ids=["in-a-commit", "without-a-commit"])
def test_a_started_feature_completed_holds_its_completed_time_to_the_second_and_its_evidence(
    commit: Evidence,
) -> None:
    assert completed_feature(STARTED, DONE, commit) == CompletedFeature(
        ONE,
        "a title",
        "why",
        ("a criterion", "another"),
        CREATED,
        ON.replace(microsecond=0),
        DONE.replace(microsecond=0),
        commit,
    )


@pytest.mark.model
def test_a_feature_in_backlog_completed_is_refused() -> None:
    with pytest.raises(NotStartedError, match=r"^F-0001 is in Backlog: start it first$"):
        completed_feature(FEATURE, DONE, COMMIT)


@pytest.mark.model
def test_a_completed_feature_completed_once_more_is_refused() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^F-0001 is completed already$"):
        completed_feature(COMPLETED, DONE, COMMIT)


@pytest.mark.model
def test_a_completed_feature_started_is_refused() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^F-0001 is completed already$"):
        started_feature(COMPLETED, DONE)


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
def test_a_completed_feature_is_written_with_its_state_line_its_two_times_and_its_commit(
    tmp_path: Path,
) -> None:
    write_feature(tmp_path, COMPLETED)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8")) == {
        "id": "F-0001",
        "state": "completed",
        "title": "a title",
        "description": "why",
        "created": CREATED,
        "started": ON.replace(microsecond=0),
        "completed": DONE.replace(microsecond=0),
        "commit": "abc1234",
        "criteria": ["a criterion", "another"],
    }


@pytest.mark.edge
def test_a_feature_completed_without_a_commit_is_written_without_one(tmp_path: Path) -> None:
    write_feature(tmp_path, completed_feature(STARTED, DONE, NO_COMMIT))
    assert "commit" not in tomllib.loads((tmp_path / FILE).read_text("utf-8"))


@pytest.mark.edge
@pytest.mark.parametrize("commit", [COMMIT, NO_COMMIT], ids=["in-a-commit", "without-a-commit"])
def test_a_completed_feature_reads_back_whole(commit: Evidence, tmp_path: Path) -> None:
    completed = completed_feature(STARTED, DONE, commit)
    write_feature(tmp_path, completed)
    assert read_feature(tmp_path, ONE) == completed


@pytest.mark.edge
def test_a_file_without_a_state_line_reads_as_a_feature_in_backlog(tmp_path: Path) -> None:
    keep(tmp_path, WRITTEN_BEFORE)
    assert read_feature(tmp_path, ONE) == FEATURE


@pytest.mark.edge
@pytest.mark.parametrize(
    "lines",
    [
        f'state = "backlog"\n{STARTED_ON}',
        STARTED_ON,
        'state = "started"\n',
        f'state = "started"\n{STARTED_ON}{COMPLETED_ON}',
        f'state = "started"\n{STARTED_ON}commit = "abc1234"\n',
        'state = "completed"\n',
        f'state = "completed"\n{COMPLETED_ON}',
        f'state = "completed"\n{STARTED_ON}{COMPLETED_ON}commit = "xyz"\n',
        'state = "removed"\n',
    ],
    ids=[
        "in-backlog-with-a-started-time",
        "no-state-line-with-a-started-time",
        "started-without-its-time",
        "started-with-a-completed-time",
        "started-with-a-commit",
        "completed-without-its-times",
        "completed-without-its-started-time",
        "completed-in-what-is-no-commit",
        "a-state-a-feature-has-not",
    ],
)
def test_a_file_whose_state_line_and_what_it_holds_disagree_is_refused_naming_it(
    lines: str, tmp_path: Path
) -> None:
    keep(tmp_path, f"{lines}{WRITTEN_BEFORE}")
    with pytest.raises(FeatureFileError, match=r"F-0001.toml holds no Feature: "):
        read_feature(tmp_path, ONE)
