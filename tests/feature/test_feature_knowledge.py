"""The knowledge a Feature keeps: a line noted in any state, in order, read back whole."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.feature import (
    FeatureState,
    blocked_feature,
    completed_feature,
    feature_detail,
    make_feature,
    note_feature,
    noted_feature,
    read_feature,
    removed_feature,
    started_feature,
    unblocked_feature,
    write_feature,
)
from flowgraph.feature_amend import FeatureAmendment, amended_feature
from flowgraph.knowledge import DECISION, FINDING, make_knowledge_line
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
FIRST = make_knowledge_line(FINDING, "the first", ON)
SECOND = make_knowledge_line(DECISION, "the second", ON)
ID = make_feature_id(1)
BARE = make_feature(ID, "a title", ["a criterion"], "", CREATED)
STARTED = started_feature(BARE, ON)
BLOCKED = blocked_feature(STARTED, "a reason", "the sponsor", ON)
COMPLETED = completed_feature(STARTED, ON, make_commit("abc1234"))
REMOVED = removed_feature(BARE, "a reason", ON)


@pytest.mark.parametrize(
    "feature",
    [BARE, STARTED, BLOCKED, COMPLETED, REMOVED],
    ids=["backlog", "started", "blocked", "completed", "removed"],
)
def test_a_line_noted_in_any_state_is_read_back_whole(
    tmp_path: Path, feature: FeatureState
) -> None:
    (tmp_path / "items").mkdir()
    write_feature(tmp_path, noted_feature(noted_feature(feature, FIRST), SECOND))
    assert read_feature(tmp_path, ID).knowledge == (FIRST, SECOND)


def test_a_line_is_kept_after_the_lines_noted_before_it() -> None:
    assert noted_feature(noted_feature(BARE, FIRST), SECOND).knowledge == (FIRST, SECOND)


def test_the_lines_are_kept_through_every_move() -> None:
    noted = noted_feature(BARE, FIRST)
    blocked = blocked_feature(started_feature(noted, ON), "a reason", "the sponsor", ON)
    done = completed_feature(unblocked_feature(blocked), ON, make_commit("abc1234"))
    assert done.knowledge == (FIRST,)


def test_the_lines_are_kept_by_the_removal() -> None:
    assert removed_feature(noted_feature(BARE, FIRST), "a reason", ON).knowledge == (FIRST,)


def test_the_lines_are_kept_by_an_amend() -> None:
    amended = amended_feature(noted_feature(BARE, FIRST), FeatureAmendment(title="another"))
    assert amended.knowledge == (FIRST,)


def test_the_detail_lists_the_lines_by_kind_time_and_text() -> None:
    detail = feature_detail(noted_feature(BARE, FIRST))
    assert [(row.kind, row.noted, row.text) for row in detail.knowledge] == [
        ("finding", ON, "the first")
    ]


def test_a_blank_text_is_refused_and_nothing_is_saved() -> None:
    saved: list[FeatureState] = []
    with pytest.raises(EmptyPartError, match=r"^text is empty$"):
        note_feature(
            feature_id=ID,
            kind=FINDING,
            text=" ",
            load_feature=lambda _: BARE,
            save_feature=saved.append,
            now=lambda: ON,
        )
    assert saved == []
