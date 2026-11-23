"""The spellings of an id: any case, the dash left out, the leading zeros left out."""

import pytest

from flowgraph.item.id import id_spelled

pytestmark = pytest.mark.edge


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        ("f15", "F-0015"),
        ("f-15", "F-0015"),
        ("F15", "F-0015"),
        ("F-15", "F-0015"),
        ("f-0015", "F-0015"),
        ("F-0015", "F-0015"),
        ("s3", "S-0003"),
        ("u-2", "U-0002"),
        ("b007", "B-0007"),
        ("Q12", "Q-0012"),
        ("t381", "T-0381"),
        ("f12345", "F-12345"),
    ],
)
def test_a_prefix_letter_of_a_kind_with_a_number_is_the_canonical_id(
    text: str, canonical: str
) -> None:
    assert id_spelled(text) == canonical


@pytest.mark.parametrize(
    "text",
    [
        *("f0", "f-0", "s0", "T-0000", "x15", "sp-15", "f", "f-", "15", "f15a", "f-15-1", "f 15"),
        *("none", "", "tests/f15", "f1.5", "f+15", "f--15", "a-term-name"),
    ],
)
def test_a_text_that_is_not_such_an_id_is_given_back_unchanged(text: str) -> None:
    assert id_spelled(text) == text
