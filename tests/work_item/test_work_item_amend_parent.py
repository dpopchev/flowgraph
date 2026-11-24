"""The parent of a work item amended: in Backlog it is put under a Feature, or taken out of one.

The Feature it is put under and the one it is taken out of are in Backlog, as it is.
"""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import make_commit, make_scenario
from flowgraph.feature import (
    FeatureNotFoundError,
    FeatureState,
    LoadFeature,
    blocked_feature,
    completed_feature,
    make_feature,
    started_feature,
)
from flowgraph.feature.move import check_move
from flowgraph.parent import (
    STANDALONE,
    FeatureId,
    FeatureIdError,
    Parent,
    make_feature_id,
    parent_asked,
)
from flowgraph.task import (
    BlockedError,
    CompletedAlreadyError,
    StartedAlreadyError,
    make_task,
    make_task_id,
)
from flowgraph.work_item import (
    Amendment,
    WorkItem,
    WorkItemId,
    WorkItemState,
    amend_work_item,
    amended_work_item,
    append_task,
    make_kind,
    make_work_item,
    make_work_item_id,
)

CHORE = make_kind("Chore", "a", "CH")
ONE = make_work_item_id(CHORE, 1)
ABOVE, OTHER, MISSING = make_feature_id(1), make_feature_id(2), make_feature_id(9)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
TASK = make_task(make_task_id(3), "a task title", "an output", "", CREATED)
ALONE = append_task(make_work_item(ONE, "a title", SCENARIO, "why", CREATED), TASK)
UNDER = replace(ALONE, parent=ABOVE)
IN_BACKLOG = make_feature(ABOVE, "a feature title", ["a criterion"], "", CREATED)
BEGUN = started_feature(IN_BACKLOG, ON)
STUCK = blocked_feature(BEGUN, "a reason", "the sponsor", ON)
LANDED = completed_feature(BEGUN, ON, make_commit("abc1234"))

# A move of the work item between two parents, as the check of an amend is asked it.
type Move = tuple[WorkItemId, Parent, Parent]


def never(*_: object) -> Never:
    """A check that an amend which leaves the parent as it was never asks for."""
    raise AssertionError("an amend that moves the work item nowhere checks no Feature")


def features(first: FeatureState = IN_BACKLOG, second: FeatureState | None = None) -> LoadFeature:
    """The load of a record holding that Feature as F-0001 and, when given, one as F-0002."""
    held = {ABOVE: first} if second is None else {ABOVE: first, OTHER: replace(second, id=OTHER)}

    def load_feature(feature_id: FeatureId) -> FeatureState:
        if feature_id not in held:
            raise FeatureNotFoundError(feature_id)
        return held[feature_id]

    return load_feature


@pytest.mark.model
@pytest.mark.parametrize(
    ("text", "parent"),
    [("F-0001", ABOVE), ("none", STANDALONE)],
    ids=["a-feature", "none"],
)
def test_the_parent_asked_for_is_the_feature_of_that_id_or_standing_alone(
    text: str, parent: Parent
) -> None:
    assert parent_asked(text) == parent


@pytest.mark.model
@pytest.mark.parametrize("text", ["S-0001", "", "None"], ids=["a-story", "nothing", "a-capital"])
def test_a_parent_asked_for_that_is_neither_is_refused_naming_none(text: str) -> None:
    refusal = rf"^'{text}' is neither a Feature id nor none: a Feature id is F- and a number$"
    with pytest.raises(FeatureIdError, match=refusal):
        parent_asked(text)


@pytest.mark.model
@pytest.mark.parametrize(
    ("item", "amendment", "amended"),
    [
        (ALONE, Amendment(parent=ABOVE), UNDER),
        (UNDER, Amendment(parent=STANDALONE), ALONE),
        (UNDER, Amendment(parent=OTHER), replace(ALONE, parent=OTHER)),
        (UNDER, Amendment(parent=ABOVE), UNDER),
        (ALONE, Amendment(title="one more", parent=ABOVE), replace(UNDER, title="one more")),
    ],
    ids=["put-under", "taken-out", "to-another", "the-one-it-has", "beside-a-title"],
)
def test_the_parent_named_is_rewritten_and_the_rest_is_as_it_was(
    item: WorkItem, amendment: Amendment, amended: WorkItem
) -> None:
    assert amended_work_item(item, amendment) == amended


@pytest.mark.command
def test_a_work_item_put_under_a_feature_is_saved_whole() -> None:
    saved: list[WorkItemState] = []
    amend_work_item(
        item_id=ONE,
        amendment=Amendment(parent=ABOVE),
        load_work_item=lambda _: ALONE,
        save_work_item=saved.append,
        check_move=lambda *_: None,
        check_realizes=never,
    )
    assert saved == [UNDER]


@pytest.mark.command
def test_a_move_is_checked_from_the_parent_it_had_to_the_one_named() -> None:
    asked: list[Move] = []
    amend_work_item(
        item_id=ONE,
        amendment=Amendment(parent=OTHER),
        load_work_item=lambda _: UNDER,
        save_work_item=lambda _: None,
        check_move=lambda *move: asked.append(move),
        check_realizes=never,
    )
    assert asked == [(ONE, ABOVE, OTHER)]


@pytest.mark.command
@pytest.mark.parametrize(
    "amendment",
    [Amendment(parent=ABOVE), Amendment(title="one more")],
    ids=["the-parent-it-has", "no-parent-named"],
)
def test_an_amend_that_leaves_the_parent_as_it_was_checks_no_feature(amendment: Amendment) -> None:
    saved: list[WorkItemState] = []
    amend_work_item(
        item_id=ONE,
        amendment=amendment,
        load_work_item=lambda _: UNDER,
        save_work_item=saved.append,
        check_move=never,
        check_realizes=never,
    )
    assert saved == [amended_work_item(UNDER, amendment)]


@pytest.mark.command
def test_a_move_refused_saves_nothing() -> None:
    saved: list[WorkItemState] = []

    def refuse(*_: object) -> Never:
        raise StartedAlreadyError("F-0001 is started already")

    with pytest.raises(StartedAlreadyError):
        amend_work_item(
            item_id=ONE,
            amendment=Amendment(title="one more", parent=ABOVE),
            load_work_item=lambda _: ALONE,
            save_work_item=saved.append,
            check_move=refuse,
            check_realizes=never,
        )
    assert saved == []


@pytest.mark.view
@pytest.mark.parametrize(
    ("was", "now"),
    [(STANDALONE, ABOVE), (ABOVE, STANDALONE), (ABOVE, OTHER)],
    ids=["put-under", "taken-out", "to-another"],
)
def test_a_move_between_features_in_backlog_passes(was: Parent, now: Parent) -> None:
    assert check_move(features(IN_BACKLOG, IN_BACKLOG), ONE, was, now) is None


@pytest.mark.view
@pytest.mark.parametrize("feature", [BEGUN, STUCK], ids=["started", "blocked"])
def test_a_work_item_is_put_under_a_started_or_a_blocked_feature_as_an_add_puts_it(
    feature: FeatureState,
) -> None:
    assert check_move(features(feature), ONE, STANDALONE, ABOVE) is None


@pytest.mark.view
def test_a_work_item_is_not_put_under_a_completed_feature() -> None:
    with pytest.raises(
        CompletedAlreadyError, match=r"^CH-0001 cannot be put under F-0001: F-0001 is completed"
    ):
        check_move(features(LANDED), ONE, STANDALONE, ABOVE)


@pytest.mark.view
@pytest.mark.parametrize(
    ("feature", "refusal", "why"),
    [
        (BEGUN, StartedAlreadyError, "F-0001 is started already"),
        (STUCK, BlockedError, "F-0001 is blocked"),
        (LANDED, CompletedAlreadyError, "F-0001 is completed already"),
    ],
    ids=["started", "blocked", "completed"],
)
def test_a_work_item_is_not_taken_out_of_a_feature_past_backlog(
    feature: FeatureState, refusal: type[Exception], why: str
) -> None:
    with pytest.raises(refusal, match=rf"^CH-0001 cannot be taken out of F-0001: {why}$"):
        check_move(features(feature, IN_BACKLOG), ONE, ABOVE, OTHER)


@pytest.mark.view
def test_a_work_item_is_not_put_under_a_feature_the_record_does_not_hold() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0009 in the record$"):
        check_move(features(), ONE, STANDALONE, MISSING)
