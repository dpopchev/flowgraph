"""A Feature file whose time holds no offset is refused when read, naming the file and the key."""

import re
import tomllib
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import tomli_w

from flowgraph.criterion import make_commit
from flowgraph.feature import (
    FeatureFileError,
    FeatureState,
    blocked_feature,
    completed_feature,
    make_feature,
    noted_feature,
    read_feature,
    removed_feature,
    started_feature,
    write_feature,
)
from flowgraph.knowledge import FINDING, make_knowledge_line
from flowgraph.parent import make_feature_id

pytestmark = pytest.mark.edge

CREATED = datetime(2026, 1, 1, 12, 30, 15, tzinfo=UTC)
ON = datetime(2026, 1, 2, 9, 0, 0, tzinfo=UTC)
FIRST = make_knowledge_line(FINDING, "the first", ON)
ID = make_feature_id(1)
BARE = make_feature(ID, "a title", ["a criterion"], "", CREATED)
STARTED = started_feature(BARE, ON)
BLOCKED = blocked_feature(STARTED, "a reason", "the sponsor", ON)
COMPLETED = completed_feature(STARTED, ON, make_commit("abc1234"))
REMOVED = removed_feature(BARE, "a reason", ON)
FILE = Path("items") / "F-0001.toml"
DAY = date(2026, 10, 11)


def rewritten(path: Path, value: object, *keys: str | int) -> None:
    """Write the file again with the value at the end of the keys."""
    held = tomllib.loads(path.read_text("utf-8"))
    place: Any = held
    for key in keys[:-1]:
        place = place[key]
    place[keys[-1]] = value
    path.write_text(tomli_w.dumps(held), "utf-8")


@pytest.mark.parametrize(
    ("feature", "keys", "key"),
    [
        (BARE, ("created",), "created"),
        (STARTED, ("started",), "started"),
        (BLOCKED, ("since",), "since"),
        (COMPLETED, ("completed",), "completed"),
        (REMOVED, ("removed",), "removed"),
        (noted_feature(BARE, FIRST), ("knowledge", 0, "noted"), "noted"),
    ],
    ids=["created", "started", "since", "completed", "removed", "noted"],
)
def test_a_day_alone_in_the_file_is_refused_naming_the_file_and_the_key(
    tmp_path: Path, feature: FeatureState, keys: tuple[str | int, ...], key: str
) -> None:
    (tmp_path / "items").mkdir()
    write_feature(tmp_path, feature)
    rewritten(tmp_path / FILE, DAY, *keys)
    line = (
        f"^{re.escape(str(tmp_path / FILE))} holds no Feature: {key} = 2026-10-11 "
        r"is a time with no offset: write it with one, as 2026-01-01 09:00:00\+00:00$"
    )
    with pytest.raises(FeatureFileError, match=line):
        read_feature(tmp_path, ID)


def test_a_time_with_an_offset_is_read(tmp_path: Path) -> None:
    (tmp_path / "items").mkdir()
    write_feature(tmp_path, BARE)
    plus_two = datetime(2026, 10, 11, 9, tzinfo=timezone(timedelta(hours=2)))
    rewritten(tmp_path / FILE, plus_two, "created")
    assert read_feature(tmp_path, ID).created == plus_two
