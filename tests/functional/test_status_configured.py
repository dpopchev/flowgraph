"""The criterion of the lines and buckets the configuration sets for status and watch.

Run end to end on a record in a temporary directory, through the file adapters of the package,
each command one second after the one before it. The `config.toml` is written after the record is
built, since a file that names a key the configuration lacks refuses every command.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from flowgraph.cli import open_files, read_config, run

pytestmark = pytest.mark.functional

START = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
KEYS = '[status]\nbacklog = 2\ncompleted = 3\n\n[watch]\nbuckets = "backlog, in-progress"\n'
STATUS_KEYS = "[status]\nbacklog = 2\ncompleted = 3\n"
HEADING = re.compile(r"^\S+ \(\d+\)$")


def completed(number: int) -> list[list[str]]:
    """The commands that add the Story of that number with one Task and complete both."""
    story, task, commit = f"S-{number:04}", f"T-{number:04}", f"abc123{number}"
    return [
        ["add", "story", f"title {number}", *CRITERION],
        ["add", "task", "a task title", "--parent", story, "--output", "an output"],
        ["start", story],
        ["start", task],
        ["complete", task, "--commit", commit],
        ["complete", story, "--commit", commit],
    ]


BUILT = [
    *[argv for number in range(1, 5) for argv in completed(number)],
    *[["add", "story", f"title {number}", *CRITERION] for number in (5, 6, 7, 8)],
    ["add", "task", "a task title", "--parent", "S-0008", "--output", "an output"],
    ["start", "S-0008"],
]
TWO_STARTED = [
    ["add", "story", "title 1", *CRITERION],
    ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"],
    ["start", "S-0001"],
    ["add", "story", "title 2", *CRITERION],
    ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"],
    ["start", "S-0002"],
]
ONE_READY = [
    ["add", "story", "title 1", *CRITERION],
    ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"],
    ["start", "S-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1231"],
    ["add", "story", "title 2", *CRITERION],
    ["add", "task", "a task title", "--parent", "S-0002", "--output", "an output"],
    ["start", "S-0002"],
    ["start", "T-0002"],
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path, at: datetime) -> Outcome:
    """Run the command at that time in cwd, whose record is `.fgraph/`, on the files of it."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        out.append,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: at,
        load_config=read_config,
    )
    return Outcome(status, "".join(out), "".join(err))


def configured(cwd: Path, text: str) -> None:
    """Write the text as the config.toml of the record in cwd."""
    (cwd / ".fgraph" / "config.toml").write_text(text)


def after(
    cwd: Path, argvs: Sequence[Sequence[str]], text: str | None, last: Sequence[str]
) -> Outcome:
    """Run each command in cwd a second after the one before, write the text, then run the last."""
    for seconds, argv in enumerate(argvs):
        fgraph(argv, cwd, START + timedelta(seconds=seconds))
    if text is not None:
        configured(cwd, text)
    return fgraph(last, cwd, START + timedelta(seconds=len(argvs)))


def headings(out: str) -> list[str]:
    """The lines of the output that are the heading of a bucket."""
    return [line for line in out.splitlines() if HEADING.match(line)]


def from_heading(out: str, heading: str, to: str | None = None) -> list[str]:
    """The lines from that heading up to the heading `to`, or to the end of the output."""
    lines = out.splitlines()
    first = lines.index(heading)
    last = lines.index(to) if to is not None else len(lines)
    return lines[first:last]


class TestConfigShow:
    def test_config_show_lists_the_five_keys(self, tmp_path: Path) -> None:
        shown = after(tmp_path, [], None, ["config", "show"])
        assert shown.out.splitlines()[-5:] == [
            "status.backlog = 1",
            'status.in-progress = "all"',
            "status.completed = 5",
            "status.removed = 5",
            'watch.buckets = "backlog, in-progress, completed, removed"',
        ]


class TestConfigSetRefused:
    def test_a_count_of_zero_exits_with_two(self, tmp_path: Path) -> None:
        refused = after(tmp_path, [], None, ["config", "set", "status.backlog", "0"])
        assert refused.status == 2

    def test_a_count_of_zero_is_refused_with_what_the_key_takes(self, tmp_path: Path) -> None:
        refused = after(tmp_path, [], None, ["config", "set", "status.backlog", "0"])
        assert refused.err.splitlines()[-1] == (
            "fgraph: error: status.backlog is 0: it takes a count of lines of 1 or more, or all"
        )

    def test_a_word_that_is_no_bucket_exits_with_two(self, tmp_path: Path) -> None:
        refused = after(tmp_path, [], None, ["config", "set", "watch.buckets", "backlog, done"])
        assert refused.status == 2

    def test_a_word_that_is_no_bucket_is_refused_with_what_it_takes(self, tmp_path: Path) -> None:
        refused = after(tmp_path, [], None, ["config", "set", "watch.buckets", "backlog, done"])
        assert refused.err.splitlines()[-1] == (
            'fgraph: error: watch.buckets is "backlog, done": it takes the buckets to show,'
            " among backlog, in-progress, completed and removed, separated by commas"
        )


class TestFlagWinsOverKey:
    def test_status_all_exits_with_zero(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, KEYS, ["status", "--all"])
        assert listed.status == 0

    def test_status_all_lists_the_three_lines_of_the_backlog(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, KEYS, ["status", "--all"])
        assert from_heading(listed.out, "Backlog (3)", "InProgress (1)") == [
            "Backlog (3)",
            "> S-0005  []  title 5",
            "  S-0006  []  title 6",
            "  S-0007  []  title 7",
        ]

    def test_status_all_lists_the_four_lines_of_completed(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, KEYS, ["status", "--all"])
        assert from_heading(listed.out, "Completed (4)") == [
            "Completed (4)",
            "  S-0004  abc1234  title 4",
            "  S-0003  abc1233  title 3",
            "  S-0002  abc1232  title 2",
            "  S-0001  abc1231  title 1",
        ]

    def test_status_under_the_keys_holds_the_heading_of_completed(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, KEYS, ["status"])
        assert "Completed (4)" in listed.out.splitlines()


class TestStatusLists:
    def test_the_backlog_lists_two_lines_then_its_more_line(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, KEYS, ["status"])
        assert from_heading(listed.out, "Backlog (3)", "InProgress (1)") == [
            "Backlog (3)",
            "> S-0005  []  title 5",
            "  S-0006  []  title 6",
            "  ... 1 more, 0 can start",
        ]

    def test_completed_lists_three_lines_then_its_more_line(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, KEYS, ["status"])
        assert from_heading(listed.out, "Completed (4)") == [
            "Completed (4)",
            "  S-0004  abc1234  title 4",
            "  S-0003  abc1233  title 3",
            "  S-0002  abc1232  title 2",
            "  ... 1 more",
        ]

    def test_backlog_lists_the_three_lines_of_the_backlog_and_no_more_line(
        self, tmp_path: Path
    ) -> None:
        listed = after(tmp_path, BUILT, KEYS, ["status", "--backlog"])
        assert from_heading(listed.out, "Backlog (3)", "InProgress (1)") == [
            "Backlog (3)",
            "> S-0005  []  title 5",
            "  S-0006  []  title 6",
            "  S-0007  []  title 7",
        ]

    def test_backlog_leaves_completed_at_its_three_lines(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, KEYS, ["status", "--backlog"])
        assert from_heading(listed.out, "Completed (4)")[-1] == "  ... 1 more"

    def test_a_backlog_set_to_all_lists_its_three_lines(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, '[status]\nbacklog = "all"\n', ["status"])
        assert from_heading(listed.out, "Backlog (3)", "InProgress (1)") == [
            "Backlog (3)",
            "> S-0005  []  title 5",
            "  S-0006  []  title 6",
            "  S-0007  []  title 7",
        ]

    def test_an_in_progress_set_to_one_lists_one_line_then_its_more_line(
        self, tmp_path: Path
    ) -> None:
        listed = after(tmp_path, TWO_STARTED, "[status]\nin-progress = 1\n", ["status"])
        assert from_heading(listed.out, "InProgress (2)", "Completed (0)")[-1] == "  ... 1 more"

    def test_watch_under_the_status_table_alone_lists_the_backlog_as_status_does(
        self, tmp_path: Path
    ) -> None:
        framed = after(tmp_path, BUILT, STATUS_KEYS, ["watch", "--count", "1"])
        assert from_heading(framed.out, "Backlog (3)", "InProgress (1)")[-1] == (
            "  ... 1 more, 0 can start"
        )


class TestReadyForReview:
    def test_a_top_of_in_progress_lists_a_line_ready_for_review_after_it(
        self, tmp_path: Path
    ) -> None:
        listed = after(tmp_path, ONE_READY, "[status]\nin-progress = 1\n", ["status"])
        assert from_heading(listed.out, "InProgress (2)", "Completed (0)") == [
            "InProgress (2)",
            "  S-0002  0/1 T  title 2",
            "    => T-0002  a task title",
            "? S-0001  1/1 T  title 1",
        ]


class TestWatchShows:
    def test_a_frame_holds_the_headings_of_the_backlog_and_in_progress_alone(
        self, tmp_path: Path
    ) -> None:
        framed = after(tmp_path, BUILT, KEYS, ["watch", "--count", "1"])
        assert headings(framed.out) == ["Backlog (3)", "InProgress (1)"]

    def test_all_shows_the_same_two_buckets_whole(self, tmp_path: Path) -> None:
        framed = after(tmp_path, BUILT, KEYS, ["watch", "--all", "--count", "1"])
        assert headings(framed.out) == ["Backlog (3)", "InProgress (1)"]


class TestNoConfiguration:
    def test_status_lists_one_line_of_the_backlog_then_its_more_line(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, None, ["status"])
        assert from_heading(listed.out, "Backlog (3)", "InProgress (1)") == [
            "Backlog (3)",
            "> S-0005  []  title 5",
            "  ... 2 more, 0 can start",
        ]

    def test_status_lists_the_four_lines_of_completed(self, tmp_path: Path) -> None:
        listed = after(tmp_path, BUILT, None, ["status"])
        assert len(from_heading(listed.out, "Completed (4)")) == 5

    def test_a_frame_holds_three_headings(self, tmp_path: Path) -> None:
        framed = after(tmp_path, BUILT, None, ["watch", "--count", "1"])
        assert headings(framed.out) == ["Backlog (3)", "InProgress (1)", "Completed (4)"]
