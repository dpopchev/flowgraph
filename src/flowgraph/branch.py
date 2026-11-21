"""The branch of a started work item: its slug, its name and the worktree it is checked out in.

The branch is `wi/<id>-<slug>`, checked out at `<parent>/<checkout name>.worktrees/<id>-<slug>`.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from flowgraph.work_item import WorkItemId, work_item_id_text

# The words of a title its slug is made of, when no slug is given.
SLUG_WORDS = 4

# Lower-case letters and digits, in words joined by one hyphen.
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class Slug:
    """The words of a branch name after the id: lower-case letters and digits joined by hyphens."""

    text: str


@dataclass(frozen=True)
class Branch:
    """The branch of a work item and the path of the worktree it is checked out in."""

    name: str
    path: Path


class SlugError(ValueError):
    """A text that is no slug."""


def make_slug(text: str) -> Slug:
    """The slug written as the text.

    Raises SlugError when it is empty or holds anything but lower-case ASCII letters and digits
    in words joined by one hyphen.
    """
    if SLUG.fullmatch(text) is None:
        raise SlugError(
            f"{text!r} is no slug: it is lower-case letters and digits joined by hyphens"
        )
    return Slug(text)


def slug_of_title(title: str) -> Slug:
    """The slug of a title: its first four words, lower-cased, each kept to its letters and digits.

    A word left with no letter or digit is skipped. Raises SlugError when no word is left.
    """
    words = [re.sub(r"[^a-z0-9]", "", word) for word in title.lower().split()]
    return make_slug("-".join([word for word in words if word][:SLUG_WORDS]))


def branch_of(item: WorkItemId, slug: Slug, checkout: Path) -> Branch:
    """The branch of the work item and its worktree, beside the checkout it is made from."""
    leaf = f"{work_item_id_text(item)}-{slug.text}"
    return Branch(f"wi/{leaf}", checkout.parent / f"{checkout.name}.worktrees" / leaf)
