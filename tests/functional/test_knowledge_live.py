"""The criterion of S-0104: fgraph knowledge --live lists the live lines alone.

Run end to end on a record in a temporary directory, through run() of the package.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

OPEN_LINE = "2026-01-04  finding  S-0001#3  is the queue one file too  (open)\n"
STANDING_LINE = "2026-01-03  decision  S-0001#2  keep one file per item  (standing)\n"
BARE_LINE = "2026-01-02  finding  S-0001#1  the store is one file\n"

# Each command with the day of January 2026 it is run on.
STORY = (1, ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"])
FIRST_FINDING = (2, ["note", "S-0001", "--finding", "the store is one file"])
STANDING = (
    3,
    [
        "note",
        "S-0001",
        "--decision",
        "keep one file per item",
        "--standing",
        "--supersedes",
        "S-0001#1",
    ],
)
OPEN = (4, ["note", "S-0001", "--finding", "is the queue one file too", "--open"])
RECORD = [STORY, FIRST_FINDING, STANDING, OPEN]

FEATURE = (5, ["add", "feature", "a feature title", "--criterion", "a developer lists the record"])
FEATURE_SUPERSEDES = (
    5,
    ["note", "F-0001", "--decision", "the queue is one file", "--supersedes", "S-0001#3"],
)
SECOND_SUPERSEDE = (
    5,
    ["note", "S-0001", "--decision", "keep one file per kind", "--supersedes", "S-0001#2"],
)

SPIKE = [
    (1, ["add", "spike", "a spike title", "--hypothesis", "Can one file hold it?"]),
    (1, ["add", "task", "a task title", "--parent", "Q-0001", "--output", "an output"]),
    (5, ["start", "Q-0001"]),
    (5, ["start", "T-0001"]),
    (5, ["complete", "T-0001", "--commit", "abc1234"]),
    (
        5,
        [
            "complete",
            "Q-0001",
            "--commit",
            "def5678",
            "--decision",
            "yes: one file per item",
            "--answer",
            "yes",
        ],
    ),
]
SPIKE_DECIDED_LINE = "2026-01-05  decision  Q-0001  yes: one file per item (answer yes)\n"


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path, day: int = 1) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    out: list[str] = []
    err: list[str] = []
    try:
        status = run(
            argv,
            cwd,
            Path.is_dir,
            out.append,
            err.append,
            open_store=open_files,
            open_git=lambda _: None,
            now=lambda: datetime(2026, 1, day, tzinfo=UTC),
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def record(cwd: Path, script: list[tuple[int, list[str]]]) -> None:
    """Run each command of the script on its day in cwd."""
    for day, argv in script:
        fgraph(argv, cwd, day)


class TestALiveListOfARecordWithAStandingOpenAndSupersededLine:
    @pytest.fixture
    def live(self, tmp_path: Path) -> Outcome:
        record(tmp_path, RECORD)
        return fgraph(["knowledge", "--live"], tmp_path)

    def test_live_exits_with_zero(self, live: Outcome) -> None:
        assert live.status == 0

    def test_live_lists_the_standing_and_the_open_line_alone(self, live: Outcome) -> None:
        assert live.out == OPEN_LINE + STANDING_LINE


class TestALineWithNoMarkIsLiveUntilALaterLineSupersedesIt:
    def test_live_lists_the_bare_line(self, tmp_path: Path) -> None:
        record(tmp_path, RECORD[:2])
        assert fgraph(["knowledge", "--live"], tmp_path).out == BARE_LINE


class TestALiveListNarrowedToFindings:
    def test_live_of_the_finding_kind_lists_the_open_finding_alone(self, tmp_path: Path) -> None:
        record(tmp_path, RECORD)
        assert fgraph(["knowledge", "--live", "--kind", "finding"], tmp_path).out == OPEN_LINE


class TestALineOfAnotherItemSupersedingALiveLine:
    def test_live_lists_the_decision_that_supersedes_the_open_finding(
        self, tmp_path: Path
    ) -> None:
        record(tmp_path, [*RECORD, FEATURE, FEATURE_SUPERSEDES])
        assert fgraph(["knowledge", "--live"], tmp_path).out == (
            "2026-01-05  decision  F-0001#1  the queue is one file\n" + STANDING_LINE
        )


class TestASupersededLineStaysSupersededWhenItsSupersederIsSuperseded:
    def test_live_holds_neither_the_bare_nor_the_standing_line(self, tmp_path: Path) -> None:
        record(tmp_path, [*RECORD, SECOND_SUPERSEDE])
        live = fgraph(["knowledge", "--live"], tmp_path)
        assert (BARE_LINE in live.out, STANDING_LINE in live.out, live.status) == (
            False,
            False,
            0,
        )


class TestTheDecisionOfACompletedSpikeIsAlwaysLive:
    def test_live_of_the_decision_kind_lists_the_spike_and_the_standing_line(
        self, tmp_path: Path
    ) -> None:
        record(tmp_path, [*RECORD, *SPIKE])
        live = fgraph(["knowledge", "--live", "--kind", "decision"], tmp_path)
        assert live.out == SPIKE_DECIDED_LINE + STANDING_LINE


class TestARecordWithNoLiveLineSaysSo:
    def test_live_of_a_record_of_the_story_alone_says_none(self, tmp_path: Path) -> None:
        record(tmp_path, [STORY])
        live = fgraph(["knowledge", "--live"], tmp_path)
        assert (live.status, live.out) == (0, "no live knowledge lines in the record\n")

    def test_live_of_a_kind_with_no_live_line_says_so(self, tmp_path: Path) -> None:
        record(tmp_path, RECORD)
        live = fgraph(["knowledge", "--live", "--kind", "deviation"], tmp_path)
        assert live.out == "no live deviation lines in the record\n"


class TestTheListWithoutLiveStillListsEveryLine:
    def test_knowledge_lists_all_three_lines(self, tmp_path: Path) -> None:
        record(tmp_path, RECORD)
        assert fgraph(["knowledge"], tmp_path).out == OPEN_LINE + STANDING_LINE + BARE_LINE

    def test_knowledge_of_the_deviation_kind_says_none(self, tmp_path: Path) -> None:
        record(tmp_path, RECORD)
        assert fgraph(["knowledge", "--kind", "deviation"], tmp_path).out == (
            "no deviation lines in the record\n"
        )
