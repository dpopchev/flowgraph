"""The criterion of S-0154: fgraph show --format json prints a work item, a Feature and a term.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
STORY = "the story title"
RECORD = [
    ["add", "term", "gate", "--means", "a check before a landing"],
    ["add", "feature", "a feature title", "--criterion", "a developer sees it", "--about", "gate"],
    [
        *("add", "story", STORY, *CRITERION),
        *("--parent", "F-0001", "--realizes", "1", "--about", "gate"),
    ],
    ["add", "task", "a task title", "--parent", "S-0001", "--output", "changed: src/gate.py"],
    ["note", "S-0001", "--finding", "a thing learned", "--about", "gate"],
]
XFAIL = pytest.mark.xfail(strict=True, reason="S-0154: fgraph show takes no --format")
IDS = [
    pytest.param("S-0001", id="story"),
    pytest.param("F-0001", id="feature"),
    pytest.param("gate", id="term"),
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
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
            now=lambda: NOW,
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


@pytest.fixture(scope="module")
def recorded(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A record with the term gate, F-0001, S-0001 under it, T-0001 and a knowledge line."""
    path = tmp_path_factory.mktemp("show")
    for argv in RECORD:
        made = fgraph(argv, path)
        assert made.status == 0, f"{' '.join(argv)}: {made.err}"
    return path


def printed(recorded: Path, item: str, *more: str) -> Outcome:
    """The outcome of fgraph show of the item with the further arguments."""
    return fgraph(["show", item, *more], recorded)


def document(recorded: Path, item: str) -> dict[str, Any]:
    """The JSON document fgraph show --format json prints of the item."""
    return json.loads(printed(recorded, item, "--format", "json").out)


@XFAIL
class TestTheStoryAsJson:
    def test_its_id(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["id"] == "S-0001"

    def test_its_kind(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["kind"] == "story"

    def test_its_bucket(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["bucket"] == "backlog"

    def test_its_parent(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["parent"] == "F-0001"

    def test_the_number_of_the_criterion_it_realizes(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["realizes"] == 1

    def test_the_text_of_the_criterion_it_realizes(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["realized"] == "a developer sees it"

    def test_its_terms(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["about"] == ["gate"]

    def test_its_criterion(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["criterion"] == {
            "answer": None,
            "decision": None,
            "expected": None,
            "given": "a state",
            "hypothesis": None,
            "observed": None,
            "then": "another",
            "when": "an action",
        }

    def test_its_tasks(self, recorded: Path) -> None:
        tasks = document(recorded, "S-0001")["tasks"]
        assert [
            (task["id"], task["expected_output"], task["check"], task["bucket"]) for task in tasks
        ] == [("T-0001", "changed: src/gate.py", None, "backlog")]

    def test_its_knowledge(self, recorded: Path) -> None:
        lines = document(recorded, "S-0001")["knowledge"]
        assert [(line["kind"], line["text"], line["about"], line["mark"]) for line in lines] == [
            ("finding", "a thing learned", ["gate"], None)
        ]

    def test_it_holds_no_commit_yet(self, recorded: Path) -> None:
        assert document(recorded, "S-0001")["commit"] is None


@XFAIL
class TestTheFeatureAsJson:
    def test_its_id(self, recorded: Path) -> None:
        assert document(recorded, "F-0001")["id"] == "F-0001"

    def test_its_kind(self, recorded: Path) -> None:
        assert document(recorded, "F-0001")["kind"] == "feature"

    def test_its_bucket(self, recorded: Path) -> None:
        assert document(recorded, "F-0001")["bucket"] == "backlog"

    def test_its_terms(self, recorded: Path) -> None:
        assert document(recorded, "F-0001")["about"] == ["gate"]

    def test_its_work_items(self, recorded: Path) -> None:
        items = document(recorded, "F-0001")["work_items"]
        assert [(each["id"], each["bucket"], each["title"]) for each in items] == [
            ("S-0001", "backlog", STORY)
        ]

    def test_its_criteria(self, recorded: Path) -> None:
        criteria = document(recorded, "F-0001")["criteria"]
        assert [
            (each["number"], each["text"], each["realized_by"], each["met"]) for each in criteria
        ] == [(1, "a developer sees it", ["S-0001"], False)]


@XFAIL
class TestTheTermAsJson:
    def test_its_name_kind_and_meaning(self, recorded: Path) -> None:
        shown = document(recorded, "gate")
        assert (shown["name"], shown["kind"], shown["meaning"]) == (
            "gate",
            "term",
            "a check before a landing",
        )

    def test_the_day_it_was_added(self, recorded: Path) -> None:
        assert document(recorded, "gate")["added"] == "2026-01-01T00:00:00+00:00"

    def test_its_items_the_work_items_first(self, recorded: Path) -> None:
        assert document(recorded, "gate")["items"] == ["S-0001", "F-0001"]

    def test_its_knowledge(self, recorded: Path) -> None:
        lines = document(recorded, "gate")["knowledge"]
        assert [(line["item"], line["kind"], line["text"]) for line in lines] == [
            ("S-0001", "finding", "a thing learned")
        ]


class TestTheFormatOfShow:
    @XFAIL
    @pytest.mark.parametrize("item", IDS)
    def test_it_is_printed_with_sorted_keys_an_indent_of_two_and_a_newline(
        self, recorded: Path, item: str
    ) -> None:
        out = printed(recorded, item, "--format", "json").out
        assert out == json.dumps(json.loads(out), indent=2, sort_keys=True) + "\n"

    @XFAIL
    @pytest.mark.parametrize("item", IDS)
    def test_it_prints_the_same_bytes_twice(self, recorded: Path, item: str) -> None:
        first = printed(recorded, item, "--format", "json").out
        second = printed(recorded, item, "--format", "json").out
        assert second == json.dumps(json.loads(first), indent=2, sort_keys=True) + "\n"

    @XFAIL
    @pytest.mark.parametrize("item", IDS)
    def test_the_format_text_prints_what_show_prints(self, recorded: Path, item: str) -> None:
        assert printed(recorded, item, "--format", "text").out == printed(recorded, item).out

    @XFAIL
    def test_a_format_that_is_neither_is_refused_naming_both(self, recorded: Path) -> None:
        refusal = "--format 'xml' is not text or json, the two formats of show"
        assert refusal in printed(recorded, "S-0001", "--format", "xml").err

    def test_a_format_that_is_neither_exits_with_2(self, recorded: Path) -> None:
        assert printed(recorded, "S-0001", "--format", "xml").status == 2

    def test_a_format_that_is_neither_prints_nothing(self, recorded: Path) -> None:
        assert printed(recorded, "S-0001", "--format", "xml").out == ""

    def test_the_text_starts_with_the_id_and_the_title(self, recorded: Path) -> None:
        assert printed(recorded, "S-0001").out.startswith(f"S-0001  {STORY}\n")
