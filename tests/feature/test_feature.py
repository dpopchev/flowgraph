"""A Feature: its id, its criteria, its file, and the bucket derived from its work items."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.feature import (
    Feature,
    FeatureDetail,
    FeatureFileError,
    FeatureNotFoundError,
    FeatureState,
    NoCriterionError,
    add_feature,
    bucket_of,
    completed_feature,
    feature_detail,
    make_feature,
    next_feature_id,
    read_feature,
    read_feature_ids,
    started_feature,
    write_feature,
)
from flowgraph.parent import (
    STANDALONE,
    FeatureIdError,
    feature_id_text,
    make_feature_id,
    parent_text,
    parse_feature_id,
)

CREATED = datetime(2026, 1, 1, 12, 30, 15, 500, tzinfo=UTC)
ONE = make_feature_id(1)
FEATURE = make_feature(ONE, "a title", ["a criterion", "another"], "why", CREATED)
FILE = Path("items") / "F-0001.toml"


@pytest.mark.model
def test_a_feature_id_is_written_f_and_four_digits_at_least() -> None:
    assert feature_id_text(make_feature_id(7)) == "F-0007"


@pytest.mark.model
def test_a_feature_id_below_one_is_refused() -> None:
    with pytest.raises(FeatureIdError, match=r"^a Feature id counts from 1: 0 is below 1$"):
        make_feature_id(0)


@pytest.mark.model
def test_a_feature_id_is_read_from_its_text() -> None:
    assert parse_feature_id("F-0012") == make_feature_id(12)


@pytest.mark.model
def test_a_text_that_is_no_feature_id_is_refused_by_itself() -> None:
    with pytest.raises(FeatureIdError, match=r"^'S-0001' is no Feature id: it is F- and a number$"):
        parse_feature_id("S-0001")


@pytest.mark.model
def test_the_next_feature_id_is_one_above_the_highest_taken() -> None:
    assert next_feature_id([make_feature_id(3), make_feature_id(1)]) == make_feature_id(4)


@pytest.mark.model
def test_a_parent_is_written_as_the_id_of_its_feature_or_as_nothing() -> None:
    assert (parent_text(ONE), parent_text(STANDALONE)) == ("F-0001", "")


@pytest.mark.model
def test_a_feature_holds_its_criteria_and_its_created_time_to_the_second() -> None:
    made = make_feature(ONE, "a title", ["a criterion", "another"], "why", CREATED)
    assert made == Feature(
        ONE, "a title", "why", ("a criterion", "another"), CREATED.replace(microsecond=0)
    )


@pytest.mark.model
@pytest.mark.parametrize(
    ("title", "criteria", "part"),
    [(" ", ["a criterion"], "title"), ("a title", ["a criterion", " "], "criterion")],
    ids=["title", "criterion"],
)
def test_a_feature_with_a_blank_part_is_refused_naming_it(
    title: str, criteria: list[str], part: str
) -> None:
    with pytest.raises(EmptyPartError, match=rf"^{part} is empty$"):
        make_feature(ONE, title, criteria, "", CREATED)


@pytest.mark.model
def test_a_feature_without_a_criterion_is_refused() -> None:
    with pytest.raises(NoCriterionError, match=r"^a Feature states at least one criterion$"):
        make_feature(ONE, "a title", [], "", CREATED)


@pytest.mark.model
@pytest.mark.parametrize(
    ("states", "bucket"),
    [
        ([], "backlog"),
        (["backlog", "backlog"], "backlog"),
        (["backlog", "removed"], "backlog"),
        (["started", "backlog"], "in-progress"),
        (["completed", "backlog"], "in-progress"),
        (["completed", "removed"], "completed"),
        (["completed"], "completed"),
    ],
    ids=["none", "backlog", "one-removed", "one-started", "one-completed", "all-done", "done"],
)
def test_the_bucket_of_a_feature_is_derived_from_the_states_of_its_work_items(
    states: list[str], bucket: str
) -> None:
    assert bucket_of(states) == bucket


@pytest.mark.view
def test_a_feature_reads_as_its_detail() -> None:
    assert feature_detail(FEATURE) == FeatureDetail(
        "F-0001", "a title", "why", ["a criterion", "another"]
    )


@pytest.mark.view
def test_a_feature_completed_in_a_commit_reads_as_its_detail_with_the_sha() -> None:
    landed = completed_feature(started_feature(FEATURE, CREATED), CREATED, make_commit("abc1234"))
    assert feature_detail(landed).commit == "abc1234"


@pytest.mark.command
def test_a_feature_is_added_under_the_next_free_id_and_saved_whole() -> None:
    saved: list[FeatureState] = []
    add_feature(
        title="a title",
        criteria=["a criterion", "another"],
        description="why",
        find_feature_ids=lambda: ["F-0002", "F-0001"],
        save_feature=saved.append,
        now=lambda: CREATED,
    )
    assert saved == [make_feature(make_feature_id(3), "a title", FEATURE.criteria, "why", CREATED)]


@pytest.mark.edge
def test_a_feature_is_written_as_its_one_file_named_by_its_id(tmp_path: Path) -> None:
    write_feature(tmp_path, FEATURE)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8")) == {
        "id": "F-0001",
        "state": "backlog",
        "title": "a title",
        "description": "why",
        "created": CREATED.replace(microsecond=0),
        "criteria": ["a criterion", "another"],
    }


@pytest.mark.edge
def test_a_feature_reads_back_whole(tmp_path: Path) -> None:
    write_feature(tmp_path, FEATURE)
    assert read_feature(tmp_path, ONE) == FEATURE


@pytest.mark.edge
def test_a_feature_the_record_does_not_hold_is_refused_by_its_id(tmp_path: Path) -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0001 in the record$"):
        read_feature(tmp_path, ONE)


@pytest.mark.edge
def test_the_ids_of_the_features_of_a_record_are_listed(tmp_path: Path) -> None:
    write_feature(tmp_path, FEATURE)
    write_feature(
        tmp_path, make_feature(make_feature_id(2), "one more", ["a criterion"], "", CREATED)
    )
    assert sorted(read_feature_ids(tmp_path)) == ["F-0001", "F-0002"]


@pytest.mark.edge
def test_a_file_that_holds_no_feature_is_refused_naming_it(tmp_path: Path) -> None:
    (tmp_path / "items").mkdir()
    (tmp_path / FILE).write_text('id = "F-0001"\n', "utf-8")
    with pytest.raises(FeatureFileError, match=r"F-0001.toml holds no Feature: "):
        read_feature(tmp_path, ONE)
