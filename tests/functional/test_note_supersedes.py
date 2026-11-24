"""The criterion of S-0103: a later decision noted as superseding the first is listed by show.

Run end to end on the files of a record in a temporary directory, through run() of the package.
"""

import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

ADD_STORY = ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a developer lists the record"]

# Each note with the day of January 2026 it is run on.
FIRST = (1, ["note", "S-0001", "--decision", "keep one store"])
LATER = (2, ["note", "S-0001", "--decision", "keep one file per item", "--supersedes", "S-0001#1"])

REFUSAL = (
    "fgraph: error: --supersedes names {}, which is no knowledge line of the record: "
    "fgraph knowledge lists each line with its ref"
)
SHOWN_LATER = (
    "Tasks (0)\nKnowledge (2)\n"
    "  decision  2026-01-01  keep one store  (superseded by S-0001#2)\n"
    "  decision  2026-01-02  keep one file per item\n"
)


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


def noted(cwd: Path, note: tuple[int, list[str]]) -> Outcome:
    """Run the note on its day in cwd."""
    day, argv = note
    return fgraph(argv, cwd, day)


def held(cwd: Path, item: str) -> str:
    """The text of the file of the item in the record of cwd."""
    return (cwd / ".fgraph" / "items" / f"{item}.toml").read_text(encoding="utf-8")


@pytest.fixture
def story(tmp_path: Path) -> Path:
    """A record with one Story and its first decision noted."""
    fgraph(ADD_STORY, tmp_path)
    noted(tmp_path, FIRST)
    return tmp_path


class TestALaterDecisionNotedAsSupersedingTheFirst:
    @pytest.fixture
    def later(self, story: Path) -> Outcome:
        return noted(story, LATER)

    def test_note_exits_with_zero_and_says_noted(self, later: Outcome) -> None:
        assert (later.status, later.out) == (0, "noted S-0001\n")

    def test_show_lists_the_first_as_superseded_by_the_later(
        self, later: Outcome, story: Path
    ) -> None:
        assert fgraph(["show", "S-0001"], story).out.endswith(SHOWN_LATER)

    def test_knowledge_lists_each_line_under_its_ref(self, later: Outcome, story: Path) -> None:
        assert fgraph(["knowledge"], story).out == (
            "2026-01-02  decision  S-0001#2  keep one file per item\n"
            "2026-01-01  decision  S-0001#1  keep one store\n"
        )

    def test_the_later_table_alone_holds_the_refs_it_supersedes(
        self, later: Outcome, story: Path
    ) -> None:
        lines = tomllib.loads(held(story, "S-0001"))["knowledge"]
        assert (set(lines[0]), lines[1]["supersedes"]) == (
            {"kind", "text", "noted"},
            ["S-0001#1"],
        )

    def test_brief_lists_the_first_as_superseded_by_the_later(
        self, later: Outcome, story: Path
    ) -> None:
        assert "  decision  2026-01-01  keep one store  (superseded by S-0001#2)\n" in (
            fgraph(["brief", "S-0001"], story).out
        )


class TestALineOfAnotherItemSupersedingTheFirst:
    @pytest.fixture
    def before(self, story: Path) -> str:
        fgraph(ADD_STORY, story)
        return held(story, "S-0001")

    @pytest.fixture
    def other(self, before: str, story: Path) -> Outcome:
        argv = ["note", "S-0002", "--finding", "one file each", "--supersedes", "S-0001#1"]
        return fgraph(argv, story, 2)

    def test_note_exits_with_zero_and_leaves_the_file_of_the_first_as_written(
        self, other: Outcome, before: str, story: Path
    ) -> None:
        assert (other.status, held(story, "S-0001") == before) == (0, True)

    def test_show_lists_the_first_as_superseded_by_the_line_of_the_other(
        self, other: Outcome, story: Path
    ) -> None:
        assert "  decision  2026-01-01  keep one store  (superseded by S-0002#1)\n" in (
            fgraph(["show", "S-0001"], story).out
        )


def test_show_of_a_feature_lists_its_first_decision_as_superseded(tmp_path: Path) -> None:
    fgraph(ADD_FEATURE, tmp_path)
    fgraph(["note", "F-0001", "--decision", "ship in two steps"], tmp_path)
    fgraph(["note", "F-0001", "--decision", "ship in one", "--supersedes", "F-0001#1"], tmp_path)
    assert "ship in two steps  (superseded by F-0001#2)\n" in (
        fgraph(["show", "F-0001"], tmp_path).out
    )


def test_a_ref_spelled_short_supersedes_the_same_line(story: Path) -> None:
    day, argv = LATER
    fgraph([*argv[:-1], "s1#1"], story, day)
    assert fgraph(["show", "S-0001"], story).out.endswith(SHOWN_LATER)


def test_a_third_line_naming_the_first_too_is_listed_after_the_second(story: Path) -> None:
    noted(story, LATER)
    fgraph(["note", "S-0001", "--decision", "keep it", "--supersedes", "S-0001#1"], story, 3)
    assert "  decision  2026-01-01  keep one store  (superseded by S-0001#2, S-0001#3)\n" in (
        fgraph(["show", "S-0001"], story).out
    )


def test_a_line_naming_two_refs_supersedes_both(story: Path) -> None:
    fgraph(["note", "S-0001", "--decision", "keep two stores"], story, 2)
    both = ["--supersedes", "S-0001#1", "--supersedes", "S-0001#2"]
    fgraph(["note", "S-0001", "--decision", "keep none", *both], story, 3)
    assert fgraph(["show", "S-0001"], story).out.endswith(
        "  decision  2026-01-01  keep one store  (superseded by S-0001#3)\n"
        "  decision  2026-01-02  keep two stores  (superseded by S-0001#3)\n"
        "  decision  2026-01-03  keep none\n"
    )


@pytest.mark.parametrize("ref", ["S-0001#9", "S-0009#1", "S-0001", "T-0001#1", "x"])
def test_a_ref_that_names_no_line_is_refused_and_writes_nothing(ref: str, story: Path) -> None:
    day, argv = LATER
    outcome = fgraph([*argv[:-1], ref], story, day)
    shown = fgraph(["show", "S-0001"], story).out.splitlines()[-1]
    assert (outcome.status, (outcome.err.splitlines() or [""])[-1], shown) == (
        2,
        REFUSAL.format(ref),
        "  decision  2026-01-01  keep one store",
    )


def test_show_of_a_first_decision_alone_lists_it_with_nothing_after(story: Path) -> None:
    shown = fgraph(["show", "S-0001"], story).out
    assert shown.endswith("  decision  2026-01-01  keep one store\n")


def test_brief_starts_with_the_show_of_the_item_once_the_later_is_run_or_refused(
    story: Path,
) -> None:
    noted(story, LATER)
    assert fgraph(["brief", "S-0001"], story).out.startswith(fgraph(["show", "S-0001"], story).out)
