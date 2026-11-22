"""The branch of a work item: its slug, its name and the path of its worktree."""

from pathlib import Path

import pytest

from flowgraph.development.branch import (
    Branch,
    SlugError,
    branch_of,
    check_slug_branched,
    make_slug,
    slug_of_title,
)
from flowgraph.work_item import make_kind, make_work_item_id

pytestmark = pytest.mark.model

CHORE = make_kind("Chore", "a", "CH")
SEVEN = make_work_item_id(CHORE, 7)


def test_a_slug_of_letters_digits_and_hyphens_is_kept_as_written() -> None:
    assert make_slug("branch-on-start-2").text == "branch-on-start-2"


@pytest.mark.parametrize(
    "text",
    ["", "Branch", "branch_on", "branch on", "-branch", "branch-", "branch--on", "brånch"],
    ids=["empty", "upper", "underscore", "space", "leading", "trailing", "double", "non-ascii"],
)
def test_a_slug_holding_another_character_is_refused(text: str) -> None:
    with pytest.raises(SlugError, match=r"is no slug: it is lower-case letters and digits"):
        make_slug(text)


def test_the_slug_of_a_title_is_its_first_four_words_lower_cased() -> None:
    assert slug_of_title("Cut the git commands a developer runs") == make_slug(
        "cut-the-git-commands"
    )


def test_the_slug_of_a_title_drops_every_character_but_a_letter_or_a_digit() -> None:
    assert slug_of_title("Raise S-0001's parts: 3") == make_slug("raise-s0001s-parts-3")


def test_the_slug_of_a_title_skips_a_word_with_no_letter_or_digit() -> None:
    assert slug_of_title("Cut -> the 1 ones") == make_slug("cut-the-1-ones")


def test_the_slug_of_a_title_with_no_letter_or_digit_is_refused() -> None:
    with pytest.raises(SlugError):
        slug_of_title("-> !")


def test_the_branch_of_a_work_item_is_named_by_its_id_and_slug() -> None:
    assert branch_of(SEVEN, make_slug("on-start"), Path("/src/project")).name == (
        "wi/CH-0007-on-start"
    )


def test_the_worktree_of_a_branch_sits_beside_the_checkout() -> None:
    assert branch_of(SEVEN, make_slug("on-start"), Path("/src/project")) == Branch(
        "wi/CH-0007-on-start", Path("/src/project.worktrees/CH-0007-on-start")
    )


def test_a_slug_given_to_a_start_with_the_development_off_is_refused_naming_the_key() -> None:
    with pytest.raises(
        SlugError,
        match=(
            r"^S-0001 takes no --slug: the development is off, so its start makes no branch"
            r" -- set development\.enabled = true in /src/project/\.fgraph/config\.toml$"
        ),
    ):
        check_slug_branched("S-0001", "a-slug", False, Path("/src/project/.fgraph/config.toml"))


@pytest.mark.parametrize(
    ("slug", "development_on"), [("a-slug", True), (None, False)], ids=["on", "no-slug"]
)
def test_a_start_that_branches_or_is_given_no_slug_is_taken(
    slug: str | None, development_on: bool
) -> None:
    assert check_slug_branched("S-0001", slug, development_on, Path("/src/config.toml")) is None
