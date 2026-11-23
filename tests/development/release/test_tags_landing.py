"""Which landings tag main: each word of `delivery.tag` against the three landings it meets."""

import pytest

from flowgraph.development.release import tags_landing
from flowgraph.record.layers import TagAt

pytestmark = pytest.mark.model


@pytest.mark.parametrize(
    ("tag", "alone", "closes", "tags"),
    [
        (TagAt.NONE, True, False, False),
        (TagAt.NONE, False, True, False),
        (TagAt.NONE, False, False, False),
        (TagAt.FEATURE_CLOSE, True, False, False),
        (TagAt.FEATURE_CLOSE, False, True, True),
        (TagAt.FEATURE_CLOSE, False, False, False),
        (TagAt.CLOSE, True, False, True),
        (TagAt.CLOSE, False, True, True),
        (TagAt.CLOSE, False, False, False),
    ],
    ids=[
        "none-alone",
        "none-closing-a-feature",
        "none-under-a-feature-it-does-not-close",
        "feature-close-alone",
        "feature-close-closing-a-feature",
        "feature-close-under-a-feature-it-does-not-close",
        "close-alone",
        "close-closing-a-feature",
        "close-under-a-feature-it-does-not-close",
    ],
)
def test_a_landing_tags_by_the_word_of_the_tag_and_what_it_closes(
    tag: TagAt, alone: bool, closes: bool, tags: bool
) -> None:
    assert tags_landing(tag, alone, closes) is tags
