"""The relations a work item names: its constructor, and the views over the record it is read in."""

import pytest

from flowgraph.relation import (
    RelationError,
    Relations,
    Standing,
    Waited,
    amended_by,
    closes_cycle,
    depended_on_by,
    make_relations,
    superseding,
    waiting_for,
    with_depends_on,
)

pytestmark = pytest.mark.model

DONE = Standing("Completed", True)
WAITING = Standing("Backlog", False)


def test_a_work_item_depends_on_none_by_default() -> None:
    assert Relations[str]().depends_on == ()


def test_the_relations_hold_the_ids_in_the_order_given() -> None:
    assert make_relations("S-2", ["S-3", "S-1"]).depends_on == ("S-3", "S-1")


def test_an_id_named_twice_is_kept_once() -> None:
    assert make_relations("S-2", ["S-1", "S-3", "S-1"]).depends_on == ("S-1", "S-3")


def test_a_work_item_that_names_itself_is_refused_by_name() -> None:
    with pytest.raises(RelationError, match=r"^S-2 cannot depend on itself$"):
        make_relations("S-2", ["S-1", "S-2"])


def test_a_work_item_waits_for_what_it_depends_on_that_is_not_completed() -> None:
    record = {"S-1": WAITING, "S-2": Standing("Backlog", False, ("S-1",))}
    assert waiting_for("S-2", record) == [Waited("S-1", "Backlog")]


def test_a_work_item_waits_for_each_one_not_completed_with_its_bucket() -> None:
    record = {
        "S-1": Standing("InProgress", False),
        "S-3": WAITING,
        "S-2": Standing("Backlog", False, ("S-1", "S-3")),
    }
    assert waiting_for("S-2", record) == [Waited("S-1", "InProgress"), Waited("S-3", "Backlog")]


def test_a_work_item_waits_for_nothing_once_what_it_depends_on_is_completed() -> None:
    record = {"S-1": DONE, "S-2": Standing("Backlog", False, ("S-1",))}
    assert waiting_for("S-2", record) == []


def test_a_work_item_that_depends_on_none_waits_for_nothing() -> None:
    assert waiting_for("S-1", {"S-1": WAITING}) == []


def test_a_work_item_waits_for_a_removed_one_too() -> None:
    record = {"S-1": Standing("Removed", False), "S-2": Standing("Backlog", False, ("S-1",))}
    assert waiting_for("S-2", record) == [Waited("S-1", "Removed")]


def test_a_dependency_back_on_the_item_closes_a_cycle() -> None:
    record = {"S-1": Standing("Backlog", False, ("S-2",)), "S-2": WAITING}
    assert closes_cycle("S-2", ["S-1"], record)


def test_a_dependency_back_on_the_item_through_others_closes_a_cycle() -> None:
    record = {
        "S-1": Standing("Backlog", False, ("S-3",)),
        "S-3": Standing("Backlog", False, ("S-2",)),
        "S-2": WAITING,
    }
    assert closes_cycle("S-2", ["S-1"], record)


def test_a_dependency_on_an_item_that_depends_on_nothing_closes_no_cycle() -> None:
    assert not closes_cycle("S-2", ["S-1"], {"S-1": WAITING, "S-2": WAITING})


def test_the_item_naming_itself_closes_no_cycle_for_its_constructor_refuses_it() -> None:
    assert not closes_cycle("S-2", ["S-2"], {"S-2": WAITING})


def test_a_shared_dependency_closes_no_cycle() -> None:
    record = {
        "S-1": Standing("Backlog", False, ("S-4",)),
        "S-3": Standing("Backlog", False, ("S-4",)),
        "S-4": WAITING,
        "S-2": WAITING,
    }
    assert not closes_cycle("S-2", ["S-1", "S-3"], record)


def test_the_ids_a_work_item_depends_on_are_replaced_by_those_given() -> None:
    assert with_depends_on(make_relations("S-2", ["S-1"]), "S-2", ["S-3"]).depends_on == ("S-3",)


def test_the_ids_a_work_item_depends_on_are_taken_away_by_giving_none() -> None:
    assert with_depends_on(make_relations("S-2", ["S-1"]), "S-2", []) == Relations()


def test_replacing_the_ids_refuses_the_work_item_that_names_itself() -> None:
    with pytest.raises(RelationError, match=r"^S-2 cannot depend on itself$"):
        with_depends_on(Relations(), "S-2", ["S-2"])


def test_a_work_item_supersedes_each_one_of_the_record_that_names_it_in_order() -> None:
    record = {
        "S-1": Standing("Removed", False, superseded_by="S-2"),
        "S-2": WAITING,
        "S-3": Standing("Removed", False, superseded_by="S-2"),
        "S-4": Standing("Removed", False, superseded_by="S-1"),
    }
    assert superseding("S-2", record) == ["S-1", "S-3"]


def test_a_work_item_is_amended_by_each_one_of_the_record_that_names_it_in_order() -> None:
    record = {
        "S-1": DONE,
        "S-2": Standing("Backlog", False, amends="S-1"),
        "S-3": Standing("Backlog", False, amends="S-1"),
        "S-4": Standing("Backlog", False, amends="S-2"),
    }
    assert amended_by("S-1", record) == ["S-2", "S-3"]


def test_a_work_item_amends_none_by_default() -> None:
    assert make_relations("S-2").amends is None


def test_a_work_item_that_amends_itself_is_refused() -> None:
    with pytest.raises(RelationError, match="S-2 cannot amend itself"):
        make_relations("S-2", amends="S-2")


def test_the_work_items_that_depend_on_an_item_are_read_from_the_record_in_its_order() -> None:
    record = {
        "S-1": Standing("Completed", True),
        "S-2": Standing("Backlog", False, ("S-1",)),
        "S-3": Standing("Backlog", False, ("S-4", "S-1")),
        "S-4": Standing("Backlog", False),
    }
    assert depended_on_by("S-1", record) == ["S-2", "S-3"]
