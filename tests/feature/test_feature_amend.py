"""The amend of a Feature: in Backlog, each part named is rewritten, the rest kept."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Never

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.feature import (
    Feature,
    FeatureNotFoundError,
    FeatureState,
    blocked_feature,
    completed_feature,
    make_feature,
    started_feature,
)
from flowgraph.feature.amend import FeatureAmendment, amend_named, amended_feature
from flowgraph.item.commands import Written
from flowgraph.parent import STANDALONE, CriterionPlace, FeatureId, make_feature_id
from flowgraph.record.store import FeatureStore, Store
from flowgraph.task import BlockedError, CompletedAlreadyError, StartedAlreadyError
from flowgraph.work_item import Amendment, NoPartError, NoSuchPartError

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ONE = make_feature_id(1)
FEATURE = make_feature(ONE, "a title", ["a criterion", "another"], "why", CREATED)
STARTED = started_feature(FEATURE, ON)
BLOCKED = blocked_feature(STARTED, "a reason", "someone", ON)
COMPLETED = completed_feature(STARTED, ON, make_commit("abc1234"))
RETITLED = replace(FEATURE, title="another title")
ONLY_A_FEATURE = "a Feature is amended by its title, its description and its criteria"


def never(*_: object) -> Never:
    """A read or a write of the record that the amend of a Feature never asks for."""
    raise AssertionError("the amend of a Feature reads and writes its own file alone")


def store(saved: list[FeatureState] | None = None, feature: FeatureState = FEATURE) -> Store:
    """The store of a record holding that Feature as F-0001; it notes a Feature it saves."""
    kept = [] if saved is None else saved

    def held(feature_id: FeatureId) -> FeatureState:
        if feature_id != ONE:
            raise FeatureNotFoundError(feature_id)
        return feature

    return Store(
        find_work_item_rows=never,
        load_work_item=never,
        find_work_item_detail=never,
        find_task_ids=never,
        save_work_item=never,
        load_queue=never,
        save_queue=never,
        find_changed_files=never,
        restore_files=never,
        features=FeatureStore(held, kept.append, never),
    )


@pytest.mark.model
@pytest.mark.parametrize(
    ("amendment", "amended"),
    [
        (FeatureAmendment(title="another title"), RETITLED),
        (FeatureAmendment(description="why not"), replace(FEATURE, description="why not")),
        (FeatureAmendment(criteria=("a new one",)), replace(FEATURE, criteria=("a new one",))),
        (
            FeatureAmendment(criteria=("a first", "a second", "a third")),
            replace(FEATURE, criteria=("a first", "a second", "a third")),
        ),
    ],
    ids=["title", "description", "one-criterion", "several-criteria"],
)
def test_a_part_named_is_rewritten_and_the_rest_is_as_it_was(
    amendment: FeatureAmendment, amended: Feature
) -> None:
    assert amended_feature(FEATURE, amendment) == amended


@pytest.mark.model
def test_several_parts_named_are_rewritten_together() -> None:
    amendment = FeatureAmendment("another title", "why not", ("a new one",))
    assert amended_feature(FEATURE, amendment) == replace(
        FEATURE, title="another title", description="why not", criteria=("a new one",)
    )


@pytest.mark.model
def test_a_blank_description_clears_it() -> None:
    assert amended_feature(FEATURE, FeatureAmendment(description="")).description == ""


@pytest.mark.model
@pytest.mark.parametrize(
    ("amendment", "part"),
    [
        (FeatureAmendment(title=" "), "title"),
        (FeatureAmendment(criteria=("a new one", "")), "criterion"),
    ],
    ids=["title", "criterion"],
)
def test_a_blank_title_or_criterion_is_refused(amendment: FeatureAmendment, part: str) -> None:
    with pytest.raises(EmptyPartError, match=rf"^{part} is empty$"):
        amended_feature(FEATURE, amendment)


@pytest.mark.model
def test_an_amendment_naming_no_part_is_refused() -> None:
    with pytest.raises(NoPartError, match=r"^amend rewrites no part of F-0001: name one$"):
        amended_feature(FEATURE, FeatureAmendment())


@pytest.mark.model
@pytest.mark.parametrize(
    ("feature", "refusal", "error"),
    [
        (STARTED, StartedAlreadyError, r"^F-0001 is started already$"),
        (BLOCKED, BlockedError, r"^F-0001 is blocked$"),
        (COMPLETED, CompletedAlreadyError, r"^F-0001 is completed already$"),
    ],
    ids=["started", "blocked", "completed"],
)
def test_a_feature_that_is_not_in_backlog_is_not_amended(
    feature: FeatureState, refusal: type[Exception], error: str
) -> None:
    with pytest.raises(refusal, match=error):
        amended_feature(feature, FeatureAmendment(title="another title"))


@pytest.mark.command
def test_a_feature_amended_says_its_id_and_the_message_of_its_commit() -> None:
    amended = amend_named("F-0001", Amendment(title="another title"), None, store())
    assert amended == Written("amended F-0001\n", "chore: amend F-0001 in the record")


@pytest.mark.command
def test_a_feature_amended_is_saved_whole_with_the_criteria_given_in_place_of_its_own() -> None:
    saved: list[FeatureState] = []
    amend_named("F-0001", Amendment(title="another title"), ["a new one", "a second"], store(saved))
    assert saved == [replace(RETITLED, criteria=("a new one", "a second"))]


@pytest.mark.command
@pytest.mark.parametrize(
    ("parts", "named"),
    [
        (Amendment(given="a state"), "given"),
        (Amendment(when="an action"), "when"),
        (Amendment(then="another"), "then"),
        (Amendment(observed="what happens"), "observed"),
        (Amendment(expected="what we wish"), "expected"),
        (Amendment(hypothesis="a question"), "hypothesis"),
        (Amendment(parent=STANDALONE), "parent"),
        (Amendment(realizes=CriterionPlace(1)), "realizes"),
        (Amendment(output="an output"), "output"),
        (Amendment(check="make test"), "check"),
        (Amendment(title="another title", given="a state", then="another"), "given, then"),
    ],
    ids=[
        "given",
        "when",
        "then",
        "observed",
        "expected",
        "hypothesis",
        "parent",
        "realizes",
        "output",
        "check",
        "beside-a-title",
    ],
)
def test_a_part_of_a_work_item_given_to_a_feature_is_refused_naming_it(
    parts: Amendment, named: str
) -> None:
    with pytest.raises(NoSuchPartError, match=rf"^F-0001 has no {named}: {ONLY_A_FEATURE}$"):
        amend_named("F-0001", parts, None, store())


@pytest.mark.command
def test_a_feature_the_record_does_not_hold_is_not_amended() -> None:
    with pytest.raises(FeatureNotFoundError, match=r"^no Feature F-0009 in the record$"):
        amend_named("F-0009", Amendment(title="another title"), None, store())


@pytest.mark.command
def test_an_amend_of_a_started_feature_saves_nothing() -> None:
    saved: list[FeatureState] = []
    with pytest.raises(StartedAlreadyError):
        amend_named("F-0001", Amendment(title="another title"), None, store(saved, STARTED))
    assert saved == []


@pytest.mark.command
def test_criteria_given_to_a_work_item_are_refused() -> None:
    with pytest.raises(
        NoSuchPartError, match=r"^S-0001 has no criteria: only a Feature states them$"
    ):
        amend_named("S-0001", Amendment(title="another title"), ["a criterion"], store())
