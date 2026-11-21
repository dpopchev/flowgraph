"""The criterion of a kind: a work item carries the criterion its kind takes, in its file too."""

import tomllib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.criterion import (
    CriterionError,
    Defect,
    EmptyPartError,
    Scenario,
    make_defect,
    make_scenario,
)
from flowgraph.work_item import (
    Amendment,
    NoSuchPartError,
    WorkItemFileError,
    WorkItemState,
    add_work_item,
    amended_work_item,
    make_kind,
    make_work_item,
    make_work_item_id,
    read_work_item,
    read_work_item_detail,
    work_item_detail,
    write_work_item,
)

CHORE = make_kind("Chore", "a", "CH")
FAULT = make_kind("Fault", "a", "FA", Defect)
ONE = make_work_item_id(FAULT, 1)
CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
SCENARIO = make_scenario("a state", "an action", "another state")
DEFECT = make_defect("it prints a traceback", "it exits 2")
ITEM = make_work_item(ONE, "a title", DEFECT, "", CREATED)
PLAIN = make_work_item(make_work_item_id(CHORE, 1), "a title", SCENARIO, "", CREATED)
FILE = Path("items") / "FA-0001.toml"


@pytest.mark.model
def test_a_defect_states_what_is_observed_and_what_is_expected() -> None:
    assert make_defect("a traceback", "exit 2") == Defect("a traceback", "exit 2")


@pytest.mark.model
@pytest.mark.parametrize(
    ("observed", "expected", "part"),
    [(" ", "exit 2", "observed"), ("a traceback", "", "expected")],
    ids=["observed", "expected"],
)
def test_a_defect_with_a_blank_part_is_refused_naming_it(
    observed: str, expected: str, part: str
) -> None:
    with pytest.raises(EmptyPartError, match=rf"^{part} is empty$"):
        make_defect(observed, expected)


@pytest.mark.model
def test_a_kind_takes_a_given_when_then_unless_it_names_another_criterion() -> None:
    assert (CHORE.takes, FAULT.takes) == (Scenario, Defect)


@pytest.mark.model
def test_a_work_item_carries_the_criterion_its_kind_takes() -> None:
    assert ITEM.criterion == DEFECT


@pytest.mark.model
def test_a_work_item_made_with_the_criterion_of_another_kind_is_refused() -> None:
    with pytest.raises(
        CriterionError,
        match=r"^a Fault states what is observed and expected, not a Given / When / Then$",
    ):
        make_work_item(ONE, "a title", SCENARIO, "", CREATED)


@pytest.mark.model
def test_what_is_expected_of_a_defect_is_amended_alone() -> None:
    amended = amended_work_item(ITEM, Amendment(expected="it exits 2 and names the path"))
    assert amended.criterion == Defect("it prints a traceback", "it exits 2 and names the path")


@pytest.mark.model
def test_a_blank_part_of_a_defect_is_not_amended_in() -> None:
    with pytest.raises(EmptyPartError, match=r"^observed is empty$"):
        amended_work_item(ITEM, Amendment(observed=" "))


@pytest.mark.model
def test_a_part_of_a_given_when_then_is_refused_on_a_defect() -> None:
    with pytest.raises(
        NoSuchPartError,
        match=r"^FA-0001 has no given, when or then: it states what is observed and expected$",
    ):
        amended_work_item(ITEM, Amendment(given="a state"))


@pytest.mark.model
def test_a_part_of_a_defect_is_refused_on_a_given_when_then() -> None:
    with pytest.raises(
        NoSuchPartError,
        match=r"^CH-0001 has no observed or expected: it states a Given / When / Then$",
    ):
        amended_work_item(PLAIN, Amendment(observed="a traceback"))


@pytest.mark.view
def test_the_detail_of_a_work_item_with_a_defect_names_what_is_observed_and_expected() -> None:
    detail = work_item_detail(ITEM)
    assert (detail.observed, detail.expected, detail.given) == (
        "it prints a traceback",
        "it exits 2",
        "",
    )


@pytest.mark.command
def test_a_work_item_is_added_with_the_criterion_given() -> None:
    saved: list[WorkItemState] = []
    add_work_item(
        kind=FAULT,
        title="a title",
        criterion=DEFECT,
        description="",
        find_work_item_rows=lambda: [],
        save_work_item=saved.append,
        now=lambda: CREATED,
    )
    assert saved == [ITEM]


@pytest.mark.edge
def test_a_defect_is_written_as_the_criterion_table_of_the_file(tmp_path: Path) -> None:
    write_work_item(tmp_path, ITEM)
    assert tomllib.loads((tmp_path / FILE).read_text("utf-8"))["criterion"] == {
        "observed": "it prints a traceback",
        "expected": "it exits 2",
    }


@pytest.mark.edge
def test_a_work_item_with_a_defect_reads_back_whole(tmp_path: Path) -> None:
    write_work_item(tmp_path, ITEM)
    assert read_work_item(tmp_path, ONE) == ITEM


@pytest.mark.edge
def test_the_detail_read_from_the_file_names_what_is_observed_and_expected(
    tmp_path: Path,
) -> None:
    write_work_item(tmp_path, ITEM)
    assert read_work_item_detail(tmp_path, ONE) == work_item_detail(ITEM)


@pytest.mark.edge
def test_a_file_holding_the_criterion_of_another_kind_is_refused(tmp_path: Path) -> None:
    write_work_item(tmp_path, PLAIN)
    (tmp_path / "items" / "CH-0001.toml").rename(tmp_path / FILE)
    path = tmp_path / FILE
    path.write_text(path.read_text("utf-8").replace("CH-0001", "FA-0001"), "utf-8")
    with pytest.raises(
        WorkItemFileError,
        match=r"FA-0001.toml holds no Fault: a Fault states what is observed and expected",
    ):
        read_work_item(tmp_path, ONE)
