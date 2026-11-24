"""The hold of a landing for the developer: under `development.approver = developer` it waits."""

import pytest

from flowgraph.development.approval import ApprovalError, check_approved
from flowgraph.record import make_config

pytestmark = pytest.mark.command

ON = "[development]\nenabled = true\n"
DEVELOPER = make_config(f'{ON}approver = "developer"\n')
AGENT = make_config(f'{ON}approver = "agent"\n')
UNWRITTEN = make_config(ON)
OFF = make_config('[development]\napprover = "developer"\n')
TRUNK = make_config(f'{ON}mode = "trunk"\napprover = "developer"\n')
HELD = (
    "S-0001 cannot land: development.approver = developer, the landing waits for the developer"
    " -- run fgraph land S-0001 --approved once the developer approves it"
)


def test_under_developer_a_landing_without_approval_is_held() -> None:
    with pytest.raises(ApprovalError) as error:
        check_approved("S-0001", False, DEVELOPER)
    assert str(error.value) == HELD


def test_the_id_is_named_as_the_record_writes_it() -> None:
    with pytest.raises(ApprovalError) as error:
        check_approved("S-1", False, DEVELOPER)
    assert str(error.value).startswith("S-0001 cannot land: ")


def test_under_developer_an_approved_landing_passes() -> None:
    assert check_approved("S-0001", True, DEVELOPER) is None


@pytest.mark.parametrize("approved", [False, True], ids=["not-given", "given"])
def test_under_agent_a_landing_passes_with_or_without_the_flag(approved: bool) -> None:
    assert check_approved("S-0001", approved, AGENT) is None


def test_the_key_left_out_passes() -> None:
    assert check_approved("S-0001", False, UNWRITTEN) is None


def test_the_development_off_passes_under_developer() -> None:
    assert check_approved("S-0001", False, OFF) is None


def test_the_trunk_passes_under_developer() -> None:
    assert check_approved("S-0001", False, TRUNK) is None


def test_a_text_that_is_no_id_passes_under_developer() -> None:
    assert check_approved("nonsense", False, DEVELOPER) is None


def test_a_bug_is_held_as_a_story_is() -> None:
    with pytest.raises(ApprovalError) as error:
        check_approved("B-0001", False, DEVELOPER)
    assert str(error.value).startswith("B-0001 cannot land: ")
