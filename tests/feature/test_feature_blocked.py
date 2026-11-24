"""The blocked state of a Feature: its block, its unblock back to started, and its file."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.feature import (
    BlockedFeature,
    CompletedFeature,
    FeatureFileError,
    FeatureState,
    blocked_feature,
    completed_feature,
    feature_row,
    make_feature,
    read_feature,
    started_feature,
    unblocked_feature,
    write_feature,
)
from flowgraph.parent import make_feature_id
from flowgraph.task import BlockedError, CompletedAlreadyError, NotBlockedError, NotStartedError

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)
SINCE = datetime(2026, 1, 3, 9, 0, 0, 500, tzinfo=UTC)
DONE = datetime(2026, 1, 4, 10, 0, 0, tzinfo=UTC)
COMMIT = make_commit("abc1234")
ONE = make_feature_id(1)
FEATURE = make_feature(ONE, "a title", ["a criterion", "another"], "why", CREATED)
STARTED = started_feature(FEATURE, ON)
BLOCKED = blocked_feature(STARTED, "the budget is not agreed", "the sponsor", SINCE)
COMPLETED = completed_feature(STARTED, DONE, COMMIT)
FILE = Path("items") / "F-0001.toml"
STARTED_FILE = {
    "id": "F-0001",
    "state": "started",
    "title": "a title",
    "description": "why",
    "created": CREATED,
    "started": ON,
    "criteria": ["a criterion", "another"],
}
WRITTEN_BEFORE = (
    'id = "F-0001"\n'
    'title = "a title"\n'
    "created = 2026-01-01 12:30:15+00:00\n"
    "started = 2026-01-02 08:00:00+00:00\n"
    'criteria = ["a criterion"]\n'
)
SINCE_LINE = "since = 2026-01-03 09:00:00+00:00\n"
REASON_LINE = 'reason = "the budget is not agreed"\n'
WAITING_ON_LINE = 'waiting_on = "the sponsor"\n'


def keep(tmp_path: Path, content: str) -> None:
    """Write the content as the file of F-0001 in the record at tmp_path."""
    (tmp_path / "items").mkdir()
    (tmp_path / FILE).write_text(content, "utf-8")


def written(tmp_path: Path) -> dict[str, object]:
    """What the file of F-0001 in the record at tmp_path holds."""
    return tomllib.loads((tmp_path / FILE).read_text("utf-8"))


@pytest.mark.model
def test_a_started_feature_blocked_holds_its_started_time_and_its_block_to_the_second() -> None:
    assert blocked_feature(STARTED, "a reason", "someone", SINCE) == BlockedFeature(
        ONE,
        "a title",
        "why",
        ("a criterion", "another"),
        CREATED,
        ON,
        "a reason",
        SINCE.replace(microsecond=0),
        "someone",
    )


@pytest.mark.model
@pytest.mark.parametrize(
    ("feature", "refusal", "error"),
    [
        (FEATURE, NotStartedError, r"^F-0001 is in Backlog: start it first$"),
        (BLOCKED, BlockedError, r"^F-0001 is blocked already$"),
        (COMPLETED, CompletedAlreadyError, r"^F-0001 is completed already$"),
    ],
    ids=["in-backlog", "blocked-already", "completed"],
)
def test_the_block_of_a_feature_that_is_not_started_is_refused(
    feature: FeatureState, refusal: type[Exception], error: str
) -> None:
    with pytest.raises(refusal, match=error):
        blocked_feature(feature, "a reason", "someone", SINCE)


@pytest.mark.model
@pytest.mark.parametrize(
    ("reason", "waiting_on", "error"),
    [(" ", "someone", r"^reason is empty$"), ("a reason", "", r"^waiting on is empty$")],
    ids=["blank-reason", "blank-waiting-on"],
)
def test_a_block_with_a_blank_part_is_refused_naming_it(
    reason: str, waiting_on: str, error: str
) -> None:
    with pytest.raises(EmptyPartError, match=error):
        blocked_feature(STARTED, reason, waiting_on, SINCE)


@pytest.mark.model
def test_a_blocked_feature_unblocked_is_started_again_with_the_started_time_it_had() -> None:
    assert unblocked_feature(BLOCKED) == STARTED


@pytest.mark.model
@pytest.mark.parametrize(
    "feature", [FEATURE, STARTED, COMPLETED], ids=["in-backlog", "started", "completed"]
)
def test_the_unblock_of_a_feature_that_is_not_blocked_is_refused(feature: FeatureState) -> None:
    with pytest.raises(NotBlockedError, match=r"^F-0001 is not blocked$"):
        unblocked_feature(feature)


@pytest.mark.model
def test_a_blocked_feature_started_is_refused() -> None:
    with pytest.raises(BlockedError, match=r"^F-0001 is blocked: unblock it first$"):
        started_feature(BLOCKED, DONE)


@pytest.mark.model
def test_a_blocked_feature_completed_holds_its_started_time_and_no_block() -> None:
    assert completed_feature(BLOCKED, DONE, COMMIT) == CompletedFeature(
        ONE, "a title", "why", ("a criterion", "another"), CREATED, ON, DONE, COMMIT
    )


@pytest.mark.view
def test_the_row_of_a_blocked_feature_is_in_progress_by_its_own_state() -> None:
    assert feature_row(BLOCKED, ["completed", "backlog"]).bucket == "in-progress"


@pytest.mark.edge
def test_a_blocked_feature_is_written_with_its_state_line_its_started_time_and_its_block(
    tmp_path: Path,
) -> None:
    write_feature(tmp_path, BLOCKED)
    assert written(tmp_path) == {
        **STARTED_FILE,
        "state": "blocked",
        "since": SINCE.replace(microsecond=0),
        "reason": "the budget is not agreed",
        "waiting_on": "the sponsor",
    }


@pytest.mark.edge
def test_a_blocked_feature_reads_back_whole(tmp_path: Path) -> None:
    write_feature(tmp_path, BLOCKED)
    assert read_feature(tmp_path, ONE) == BLOCKED


@pytest.mark.edge
def test_the_block_leaves_the_file_of_a_feature_at_its_unblock(tmp_path: Path) -> None:
    write_feature(tmp_path, BLOCKED)
    write_feature(tmp_path, unblocked_feature(BLOCKED))
    assert written(tmp_path) == STARTED_FILE


@pytest.mark.edge
@pytest.mark.parametrize(
    "lines",
    [
        f'state = "blocked"\n{REASON_LINE}{WAITING_ON_LINE}',
        f'state = "blocked"\n{SINCE_LINE}{WAITING_ON_LINE}',
        f'state = "blocked"\n{SINCE_LINE}{REASON_LINE}',
        f'state = "started"\n{SINCE_LINE}{REASON_LINE}{WAITING_ON_LINE}',
    ],
    ids=[
        "blocked-without-its-time",
        "blocked-without-its-reason",
        "blocked-without-what-it-waits-on",
        "started-with-a-block",
    ],
)
def test_a_file_whose_state_line_and_the_block_it_holds_disagree_is_refused_naming_it(
    lines: str, tmp_path: Path
) -> None:
    keep(tmp_path, f"{lines}{WRITTEN_BEFORE}")
    with pytest.raises(FeatureFileError, match=r"F-0001.toml holds no Feature: "):
        read_feature(tmp_path, ONE)


@pytest.mark.edge
def test_a_blocked_file_with_a_blank_reason_is_refused_naming_it(tmp_path: Path) -> None:
    keep(
        tmp_path, f'state = "blocked"\n{SINCE_LINE}reason = " "\n{WAITING_ON_LINE}{WRITTEN_BEFORE}'
    )
    with pytest.raises(FeatureFileError, match=r"F-0001\.toml holds no Feature: reason is empty$"):
        read_feature(tmp_path, ONE)
