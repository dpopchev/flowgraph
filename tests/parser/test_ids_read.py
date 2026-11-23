"""The ids of the parsed arguments of every command are read in any spelling."""

import pytest

from flowgraph.parser.arguments import build_command_line
from flowgraph.parser.ids import ids_read

pytestmark = pytest.mark.edge

STORY = ["add", "story", "a title", "--given", "g", "--when", "w", "--then", "t"]


def read(argv: list[str]) -> dict[str, object]:
    """The arguments of the command line, parsed and read through ids_read."""
    return vars(ids_read(build_command_line().parser.parse_args(argv)))


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["show", "f15"], {"id": "F-0015"}),
        (["about", "s3"], {"id": "S-0003"}),
        (["start", "t381"], {"id": "T-0381"}),
        (["complete", "t-381", "--commit", "abc"], {"id": "T-0381"}),
        (["block", "f-15", "--reason", "why", "--waiting-on", "x"], {"id": "F-0015"}),
        (["unblock", "F15"], {"id": "F-0015"}),
        (["land", "u2"], {"id": "U-0002"}),
        (["verify", "b7", "--yes", "ok"], {"id": "B-0007"}),
        (["note", "q1", "--finding", "text"], {"id": "Q-0001"}),
        (["amend", "f15", "--title", "new"], {"id": "F-0015"}),
        (["remove", "s3", "--reason", "why"], {"id": "S-0003"}),
        (["reorder", "s3", "--before", "f15"], {"id": "S-0003", "before": "F-0015"}),
        (["remove", "s3", "--superseded-by", "s4"], {"superseded_by": "S-0004"}),
        (["amend", "s3", "--parent", "f15"], {"parent": "F-0015"}),
        (
            ["amend", "s3", "--depends-on", "s4", "--depends-on", "u-5"],
            {"depends_on": ["S-0004", "U-0005"]},
        ),
        (["add", "task", "a title", "--parent", "s3", "--output", "o"], {"parent": "S-0003"}),
        ([*STORY, "--parent", "f15"], {"parent": "F-0015"}),
        (
            [*STORY, "--depends-on", "s4", "--depends-on", "b-5"],
            {"depends_on": ["S-0004", "B-0005"]},
        ),
        ([*STORY, "--filed-during", "s4"], {"filed_during": "S-0004"}),
        ([*STORY, "--amends", "s4"], {"amends": "S-0004"}),
    ],
)
def test_every_id_of_the_arguments_is_read_in_its_canonical_form(
    argv: list[str], expected: dict[str, object]
) -> None:
    read_args = read(argv)
    assert {name: read_args[name] for name in expected} == expected


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["show", "x15"], {"id": "x15"}),
        (["show", "f-0"], {"id": "f-0"}),
        (["amend", "s3", "--parent", "none"], {"parent": "none"}),
        (["amend", "s3", "--depends-on", "none"], {"depends_on": ["none"]}),
        (["amend", "s3", "--title", "f15"], {"title": "f15"}),
        (["note", "s3", "--finding", "t", "--about", "f15"], {"about": ["f15"]}),
        (["block", "t3", "--reason", "r", "--waiting-on", "f15"], {"waiting_on": "f15"}),
        ([*STORY, "--then", "s3"], {"then": "s3"}),
    ],
)
def test_a_text_that_is_no_id_or_is_no_id_option_is_left_as_typed(
    argv: list[str], expected: dict[str, object]
) -> None:
    read_args = read(argv)
    assert {name: read_args[name] for name in expected} == expected


def test_arguments_without_an_id_are_given_back_equal() -> None:
    args = build_command_line().parser.parse_args(["status"])
    assert ids_read(args) == args
