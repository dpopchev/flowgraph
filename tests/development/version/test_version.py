"""The version of a release: its smart constructor, the last of the tags and the next one."""

from datetime import UTC, datetime

import pytest

from flowgraph.bug import BUG
from flowgraph.development.version import (
    Bump,
    Version,
    VersionError,
    bump_of,
    is_released,
    last_version,
    make_version,
    next_version,
    version_text,
)
from flowgraph.spike import SPIKE
from flowgraph.story import STORY
from flowgraph.upkeep import UPKEEP
from flowgraph.work_item import Kind

pytestmark = pytest.mark.model

TAGGED = datetime(2026, 1, 2, tzinfo=UTC)
BEFORE = datetime(2026, 1, 1, tzinfo=UTC)
AFTER = datetime(2026, 1, 3, tzinfo=UTC)


def version(text: str) -> Version:
    """The version of the text, through its smart constructor."""
    return make_version(text)


def test_a_version_is_written_back_as_its_tag() -> None:
    assert version_text(make_version("v1.20.3")) == "v1.20.3"


@pytest.mark.parametrize(
    "text",
    ["", "1.2.3", "v1.2", "v1.2.3.4", "v01.2.3", "v1.2.3-rc1", "V1.2.3", "v1.-2.3", "v1.2.x"],
    ids=["empty", "no-v", "two", "four", "leading-zero", "suffix", "capital", "minus", "letter"],
)
def test_a_text_that_is_no_version_is_refused_naming_the_form(text: str) -> None:
    with pytest.raises(
        VersionError, match=r"is no version: v<major>\.<minor>\.<patch>, as v1\.2\.3$"
    ):
        make_version(text)


def test_the_last_version_of_the_tags_is_the_highest_by_its_numbers() -> None:
    assert last_version(["v0.9.0", "v0.10.0", "v0.2.5"]) == version("v0.10.0")


def test_a_tag_that_is_no_version_is_passed_over_for_the_last() -> None:
    assert last_version(["v0.1.0", "v2.0.0-rc1", "v-latest"]) == version("v0.1.0")


def test_tags_that_hold_no_version_have_no_last() -> None:
    assert last_version(["v-latest"]) is None


@pytest.mark.parametrize(
    ("last", "bump", "expected"),
    [
        ("v0.1.0", Bump.MINOR, "v0.2.0"),
        ("v1.4.2", Bump.MINOR, "v1.5.0"),
        ("v0.1.0", Bump.PATCH, "v0.1.1"),
        ("v1.4.2", Bump.PATCH, "v1.4.3"),
    ],
    ids=["minor", "minor-resets-the-patch", "patch", "patch-keeps-the-minor"],
)
def test_the_next_version_raises_the_number_the_bump_names(
    last: str, bump: Bump, expected: str
) -> None:
    assert next_version(version(last), bump) == version(expected)


@pytest.mark.parametrize("bump", [Bump.MINOR, Bump.PATCH], ids=["minor", "patch"])
def test_the_next_version_without_a_last_is_the_first(bump: Bump) -> None:
    assert next_version(None, bump) == version("v0.1.0")


@pytest.mark.parametrize(
    ("kinds", "expected"),
    [
        ((STORY,), Bump.MINOR),
        ((BUG,), Bump.MINOR),
        ((UPKEEP, STORY, SPIKE), Bump.MINOR),
        ((UPKEEP,), Bump.PATCH),
        ((SPIKE, UPKEEP), Bump.PATCH),
        ((), None),
    ],
    ids=["a-story", "a-bug", "a-story-among-others", "an-upkeep", "a-spike-and-an-upkeep", "none"],
)
def test_the_bump_is_a_minor_for_a_story_or_a_bug_else_a_patch(
    kinds: tuple[Kind, ...], expected: Bump | None
) -> None:
    assert bump_of(kinds) == expected


@pytest.mark.parametrize(
    ("held", "completed", "expected"),
    [
        (True, AFTER, True),
        (False, BEFORE, False),
        (None, BEFORE, True),
        (None, TAGGED, True),
        (None, AFTER, False),
    ],
    ids=[
        "its-commit-held-by-the-tag",
        "its-commit-not-held",
        "no-commit-completed-before-the-tag",
        "no-commit-completed-as-the-tag",
        "no-commit-completed-after-the-tag",
    ],
)
def test_a_work_item_is_released_by_its_commit_else_by_its_time(
    held: bool | None, completed: datetime, expected: bool
) -> None:
    assert is_released(held, completed, TAGGED) is expected
