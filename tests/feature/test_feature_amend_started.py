"""The amend of a started or blocked Feature: its deviation is kept with the part rewritten.

A blocked one counts as started. The deviation is asked for once the Feature is started and
refused for one in Backlog; a Task takes none.
"""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Never

import pytest

from flowgraph.criterion import EmptyPartError, make_commit
from flowgraph.feature import (
    FeatureNotFoundError,
    FeatureState,
    blocked_feature,
    completed_feature,
    make_feature,
    noted_feature,
    started_feature,
)
from flowgraph.feature.amend import FeatureAmendment, amend_named, amended_feature
from flowgraph.item.commands import Written
from flowgraph.knowledge import DEVIATION, FINDING, make_knowledge_line
from flowgraph.parent import FeatureId, make_feature_id
from flowgraph.record.store import FeatureStore, Store
from flowgraph.task import CompletedAlreadyError
from flowgraph.work_item import Amendment, DeviationError, NoPartError

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
ONE = make_feature_id(1)
FEATURE = make_feature(ONE, "a title", ["a criterion", "another"], "why", CREATED)
STARTED = started_feature(FEATURE, ON)
BLOCKED = blocked_feature(STARTED, "a reason", "someone", ON)
COMPLETED = completed_feature(STARTED, ON, make_commit("abc1234"))
LINE = make_knowledge_line(DEVIATION, "the criteria are narrowed", ON)
KEPT = make_knowledge_line(FINDING, "a finding made before", ON)
NEEDED = (
    "^F-0001 is started: amend it with --deviation TEXT, what changes in what it was agreed to do$"
)
BOTH = pytest.mark.parametrize("feature", [STARTED, BLOCKED], ids=["started", "blocked"])


def never(*_: object) -> Never:
    """A read or a write of the record that the amend of a Feature never asks for."""
    raise AssertionError("the amend of a Feature reads and writes its own file alone")


def store(saved: list[FeatureState] | None = None, feature: FeatureState = FEATURE) -> Store:
    """The store of a record holding that Feature as F-0001, which notes a Feature it saves."""
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
@BOTH
@pytest.mark.parametrize(
    ("amendment", "part"),
    [
        (FeatureAmendment(title="another title"), {"title": "another title"}),
        (FeatureAmendment(description="why not"), {"description": "why not"}),
        (FeatureAmendment(criteria=("a new one",)), {"criteria": ("a new one",)}),
        (FeatureAmendment(about=("a term",)), {"about": ("a term",)}),
    ],
    ids=["title", "description", "criteria", "about"],
)
def test_a_part_of_a_started_feature_is_rewritten_with_its_deviation(
    feature: FeatureState, amendment: FeatureAmendment, part: dict[str, Any]
) -> None:
    amended = amended_feature(feature, amendment, LINE)
    assert amended == replace(feature, **part, knowledge=(LINE,))


@pytest.mark.model
@BOTH
def test_a_line_the_feature_kept_stays_before_the_deviation(feature: FeatureState) -> None:
    kept = noted_feature(feature, KEPT)
    amended = amended_feature(kept, FeatureAmendment(title="another title"), LINE)
    assert amended.knowledge == (KEPT, LINE)


@pytest.mark.model
@BOTH
def test_an_amend_without_a_deviation_of_a_started_feature_is_refused(
    feature: FeatureState,
) -> None:
    with pytest.raises(DeviationError, match=NEEDED):
        amended_feature(feature, FeatureAmendment(title="another title"))


@pytest.mark.model
def test_a_deviation_for_a_feature_in_backlog_is_refused() -> None:
    refusal = (
        "^F-0001 is in Backlog: it has no agreed plan to deviate from -- "
        "amend it without --deviation$"
    )
    with pytest.raises(DeviationError, match=refusal):
        amended_feature(FEATURE, FeatureAmendment(title="another title"), LINE)


@pytest.mark.model
@BOTH
def test_a_deviation_alone_amends_no_part_of_a_started_feature(feature: FeatureState) -> None:
    with pytest.raises(NoPartError, match=r"^amend rewrites no part of F-0001: name one$"):
        amended_feature(feature, FeatureAmendment(), LINE)


@pytest.mark.model
@BOTH
def test_a_blank_criterion_of_a_started_feature_is_refused(feature: FeatureState) -> None:
    with pytest.raises(EmptyPartError, match=r"^criterion is empty$"):
        amended_feature(feature, FeatureAmendment(criteria=("a new one", "")), LINE)


@pytest.mark.model
def test_a_completed_feature_is_refused_with_a_deviation() -> None:
    with pytest.raises(CompletedAlreadyError, match=r"^F-0001 is completed already$"):
        amended_feature(COMPLETED, FeatureAmendment(title="another title"), LINE)


@pytest.mark.command
def test_a_started_feature_amended_with_its_deviation_says_its_id_and_its_commit() -> None:
    written = amend_named("F-0001", Amendment(title="x"), None, store(feature=STARTED), LINE)
    assert written == Written("amended F-0001\n", "chore: amend F-0001 in the record")


@pytest.mark.command
def test_a_started_feature_amended_with_its_deviation_is_saved_once_holding_it() -> None:
    saved: list[FeatureState] = []
    amend_named("F-0001", Amendment(title="x"), None, store(saved, STARTED), LINE)
    assert saved == [replace(STARTED, title="x", knowledge=(LINE,))]


@pytest.mark.command
def test_a_task_takes_no_deviation() -> None:
    refusal = r"^T-0001 takes no --deviation: a Task keeps no knowledge line$"
    with pytest.raises(DeviationError, match=refusal):
        amend_named("T-0001", Amendment(title="x"), None, store(), LINE)
