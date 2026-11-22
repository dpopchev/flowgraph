"""The version of a release: the v* tag of the trunk, and the next one the completed work names.

A version is written `v<major>.<minor>.<patch>`, each a whole number without a leading zero.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import assert_never

from flowgraph.bug import BUG
from flowgraph.story import STORY
from flowgraph.work_item import Kind

# The text of a version, as its tag writes it.
TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")

# The kinds of work item whose completion raises the minor: a new behavior or a fixed one.
MINOR_KINDS = frozenset({STORY, BUG})


class Bump(Enum):
    """The number of the version the work completed since the last tag raises."""

    MINOR = "minor"
    PATCH = "patch"


@dataclass(frozen=True, order=True)
class Version:
    """A version of the trunk: its major, minor and patch numbers, ordered as they are."""

    major: int
    minor: int
    patch: int


class VersionError(ValueError):
    """A text that is no version: `v` and three whole numbers, as v1.2.3."""


def make_version(text: str) -> Version:
    """The version the text writes; raises VersionError for a text that writes none."""
    written = TAG.fullmatch(text)
    if written is None:
        raise VersionError(f"{text!r} is no version: v<major>.<minor>.<patch>, as v1.2.3")
    major, minor, patch = (int(number) for number in written.groups())
    return Version(major, minor, patch)


# The version of the first release, made where no tag writes a version.
FIRST = make_version("v0.1.0")


def version_text(version: Version) -> str:
    """The version as its tag writes it."""
    return f"v{version.major}.{version.minor}.{version.patch}"


def last_version(tags: Iterable[str]) -> Version | None:
    """The highest version the tags write; None when none writes one, a tag that is none passed."""
    versions = []
    for tag in tags:
        try:
            versions.append(make_version(tag))
        except VersionError:
            continue
    return max(versions, default=None)


def next_version(last: Version | None, bump: Bump) -> Version:
    """The version after the last by the bump; the first, v0.1.0, when there is no last."""
    if last is None:
        return FIRST
    match bump:
        case Bump.MINOR:
            return Version(last.major, last.minor + 1, 0)
        case Bump.PATCH:
            return Version(last.major, last.minor, last.patch + 1)
        case _ as unreachable:
            assert_never(unreachable)


def bump_of(kinds: Iterable[Kind]) -> Bump | None:
    """The bump the kinds of the work items completed since the last tag name.

    A minor when a Story or a Bug is among them, a new behavior or a fixed one; a patch for any
    other kind alone; None when no work item is completed since.
    """
    completed = set(kinds)
    if completed & MINOR_KINDS:
        return Bump.MINOR
    return Bump.PATCH if completed else None


def is_released(held: bool | None, completed: datetime, tagged: datetime) -> bool:
    """True when the last tag holds a completed work item, so it is not completed since.

    held says whether the tag holds the commit the work item names, so a work item landed just
    before the tag is held by it whatever the clocks say; it is None for a work item that names
    no commit, as one completed with the development off, or a commit git does not know: that
    one is held when it was completed by the time the tag was made.
    """
    if held is not None:
        return held
    return completed <= tagged
