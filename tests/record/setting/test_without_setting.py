"""A key taken back: the settings without it, so it reads as its default, the others kept."""

import pytest

from flowgraph.record import ConfigError
from flowgraph.record.setting import without_setting

pytestmark = pytest.mark.model

GATED = {"development": {"enabled": True, "gate": "make check"}}


def test_a_key_taken_back_leaves_its_table_without_it() -> None:
    assert without_setting(GATED, "development.gate") == {"development": {"enabled": True}}


def test_the_last_key_of_a_table_taken_back_leaves_no_table() -> None:
    assert without_setting({"git": {"commit": False}}, "git.commit") == {}


def test_the_push_of_a_landing_taken_back_leaves_no_delivery_table() -> None:
    assert without_setting({**GATED, "delivery": {"push": True}}, "delivery.push") == GATED


def test_the_tag_of_the_close_of_a_feature_taken_back_keeps_the_push() -> None:
    delivery = {"delivery": {"push": True, "tag": "feature-close"}}
    assert without_setting(delivery, "delivery.tag") == {"delivery": {"push": True}}


def test_the_driver_taken_back_keeps_the_development_enabled() -> None:
    driven = {"development": {"enabled": True, "driver": "agent"}}
    assert without_setting(driven, "development.driver") == {"development": {"enabled": True}}


def test_the_archive_board_taken_back_leaves_no_archive_table() -> None:
    assert without_setting({"archive": {"board": ".board"}}, "archive.board") == {}


def test_the_lines_of_the_backlog_taken_back_leave_the_other_status_keys() -> None:
    status = {"status": {"backlog": 3, "in-progress": "all"}}
    assert without_setting(status, "status.backlog") == {"status": {"in-progress": "all"}}


def test_the_buckets_taken_back_leave_no_watch_table() -> None:
    assert without_setting({"watch": {"buckets": "backlog"}}, "watch.buckets") == {}


def test_a_key_the_settings_do_not_hold_is_taken_back_to_the_settings_as_they_were() -> None:
    assert without_setting(GATED, "development.parallel") == GATED


def test_a_key_the_configuration_does_not_have_is_refused_naming_it() -> None:
    with pytest.raises(ConfigError, match=r"^development\.gates is no key of the configuration$"):
        without_setting(GATED, "development.gates")
