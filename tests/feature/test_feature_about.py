"""The terms a Feature is about: kept by its moves, rewritten by an amend, read back whole."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import make_commit
from flowgraph.feature import (
    FeatureState,
    blocked_feature,
    completed_feature,
    feature_detail,
    make_feature,
    noted_feature,
    read_feature,
    removed_feature,
    started_feature,
    unblocked_feature,
    write_feature,
)
from flowgraph.feature_amend import FeatureAmendment, amended_feature
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ID = make_feature_id(1)
ABOUT = make_feature(ID, "a title", ["a criterion"], "", CREATED, ("gate", "lane"))
STARTED = started_feature(ABOUT, ON)
BLOCKED = blocked_feature(STARTED, "a reason", "the sponsor", ON)


def test_a_feature_is_made_about_no_term_by_default() -> None:
    assert make_feature(ID, "a title", ["a criterion"], "", CREATED).about == ()


def test_a_feature_is_made_about_the_terms_given_in_order() -> None:
    assert ABOUT.about == ("gate", "lane")


@pytest.mark.parametrize(
    "moved",
    [
        STARTED,
        BLOCKED,
        unblocked_feature(BLOCKED),
        completed_feature(STARTED, ON, make_commit("abc1234")),
        removed_feature(ABOUT, "a reason", ON),
    ],
    ids=["started", "blocked", "unblocked", "completed", "removed"],
)
def test_a_feature_stays_about_its_terms_through_every_move(moved: FeatureState) -> None:
    assert moved.about == ("gate", "lane")


def test_the_terms_are_read_back_as_written(tmp_path: Path) -> None:
    write_feature(tmp_path, STARTED)
    assert read_feature(tmp_path, ID).about == ("gate", "lane")


def test_the_terms_are_given_by_the_detail_as_plain_data() -> None:
    assert feature_detail(ABOUT).about == ["gate", "lane"]


def test_the_terms_of_a_line_are_read_back_as_written(tmp_path: Path) -> None:
    line = make_knowledge_line(FINDING, "a text", ON, ("lane",))
    write_feature(tmp_path, noted_feature(ABOUT, line))
    assert read_feature(tmp_path, ID).knowledge[0].about == ("lane",)


def test_an_amend_gives_the_terms_in_place_of_those_it_had() -> None:
    assert amended_feature(ABOUT, FeatureAmendment(about=("lane",))).about == ("lane",)


def test_an_amend_given_no_term_takes_them_all_away() -> None:
    assert amended_feature(ABOUT, FeatureAmendment(about=())).about == ()
