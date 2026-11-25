"""The criterion of S-0156: fgraph about prints the links of an item, a term and a file as JSON.

Run end to end through `run` on a record in a real git repository in a temporary directory, never
a faked git; the identity of its commits comes from the environment and no git config is read.
"""

import json
import subprocess
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from flowgraph.cli import open_files, open_git, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
STORY_TITLE = "Raise the Stories fgraph lists from 0 to 1"
SECOND_TITLE = "Raise the Spikes fgraph lists from 0 to 1"
MEANING = "a check before a landing"
DECISION = "the work holds no state"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
RECORD = [
    ["add", "term", "gate", "--means", MEANING],
    ["add", "story", STORY_TITLE, *CRITERION, "--about", "gate"],
    ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"],
    ["start", "S-0001"],
    ["start", "T-0001"],
]
RELATIONS = [
    "feature",
    "depends_on",
    "filed_during",
    "filed_here",
    "supersedes",
    "superseded_by",
    "amends",
    "amended_by",
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


@dataclass(frozen=True)
class Checkout:
    """A repository and the shas of the commits of the Task and of the Story."""

    path: Path
    task: str
    story: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on its files and the real git."""
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
            open_git=open_git,
            now=lambda: NOW,
            load_config=read_config,
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def commit(cwd: Path, name: str, message: str, *more: str) -> str:
    """Write the file of that name, commit it and the files named after it under the message.

    The sha of the commit.
    """
    (cwd / name).write_text(f"{message}\n", encoding="utf-8")
    git(cwd, "add", name, *more)
    git(cwd, "commit", "--quiet", "--message", message)
    return git(cwd, "rev-parse", "HEAD")


def made(argv: Sequence[str], cwd: Path) -> None:
    """Run the command and fail the arrangement when it does not exit with zero."""
    outcome = fgraph(argv, cwd)
    assert outcome.status == 0, f"{' '.join(argv)}: {outcome.err}"


@pytest.fixture(scope="module")
def checkout(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Checkout]:
    """A repository whose completed S-0001 is about the term gate and S-0002 depends on it."""
    base = tmp_path_factory.mktemp("about-json").resolve()
    path = base / "project"
    path.mkdir()
    empty = base / "gitconfig"
    empty.touch()
    with pytest.MonkeyPatch.context() as environment:
        for name, value in IDENTITY.items():
            environment.setenv(name, value)
        environment.setenv("GIT_CONFIG_GLOBAL", str(empty))
        environment.setenv("GIT_CONFIG_NOSYSTEM", "1")
        git(path, "init", "--quiet", "--initial-branch", "main")
        for argv in RECORD:
            made(argv, path)
        task = commit(path, "work.txt", "feat: do the work of the Task")
        made(["complete", "T-0001", "--commit", task], path)
        (path / "story.txt").write_text("the Story\n", encoding="utf-8")
        story = commit(path, "work.txt", "feat: land the Story", "story.txt")
        made(["complete", "S-0001", "--commit", story], path)
        made(
            ["note", "S-0001", "--decision", DECISION, "--about", "gate", "--governs", "work.txt"],
            path,
        )
        made(["add", "story", SECOND_TITLE, *CRITERION, "--depends-on", "S-0001"], path)
        yield Checkout(path, task, story)


def about(checkout: Checkout, item: str, *more: str) -> Outcome:
    """The outcome of fgraph about the item with the arguments, run in the checkout."""
    return fgraph(["about", item, *more], checkout.path)


def document(checkout: Checkout, item: str) -> Any:
    """The JSON fgraph about prints of the item, parsed."""
    return json.loads(about(checkout, item, "--format", "json").out)


def canonical(text: str) -> str:
    """The text a JSON document is printed as: sorted keys, an indent of two and a newline."""
    return json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n"


class TestTheStoryAsJson:
    def test_it_holds_its_id_kind_and_title(self, checkout: Checkout) -> None:
        story = document(checkout, "S-0001")
        assert (story["id"], story["kind"], story["title"]) == ("S-0001", "story", STORY_TITLE)

    def test_it_holds_the_story_that_depends_on_it(self, checkout: Checkout) -> None:
        assert document(checkout, "S-0001")["depended_on_by"] == [
            {"bucket": "backlog", "id": "S-0002", "title": SECOND_TITLE}
        ]

    def test_it_holds_the_terms(self, checkout: Checkout) -> None:
        assert document(checkout, "S-0001")["terms"] == [{"meaning": MEANING, "name": "gate"}]

    def test_it_holds_the_knowledge(self, checkout: Checkout) -> None:
        lines = document(checkout, "S-0001")["knowledge"]
        assert [(line["kind"], line["text"], line["governs"]) for line in lines] == [
            ("decision", DECISION, ["work.txt"])
        ]

    @pytest.mark.parametrize("relation", RELATIONS)
    def test_a_relation_that_holds_nothing_is_empty(
        self, checkout: Checkout, relation: str
    ) -> None:
        assert document(checkout, "S-0001")[relation] == []


class TestTheTermAsJson:
    def test_it_holds_its_name_kind_and_meaning(self, checkout: Checkout) -> None:
        term = document(checkout, "gate")
        assert (term["name"], term["kind"], term["meaning"]) == ("gate", "term", MEANING)

    def test_it_holds_the_item_about_it(self, checkout: Checkout) -> None:
        assert document(checkout, "gate")["items"] == [{"id": "S-0001", "via": None}]

    def test_it_holds_the_line_about_it(self, checkout: Checkout) -> None:
        lines = document(checkout, "gate")["knowledge"]
        assert [(line["item"], line["text"], line["via"]) for line in lines] == [
            ("S-0001", DECISION, None)
        ]


class TestTheFileAsJson:
    def test_it_holds_its_path_and_kind(self, checkout: Checkout) -> None:
        file = document(checkout, "work.txt")
        assert (file["path"], file["kind"]) == ("work.txt", "file")

    def test_it_holds_the_line_that_governs_it(self, checkout: Checkout) -> None:
        lines = document(checkout, "work.txt")["governed_by"]
        assert [(line["item"], line["text"]) for line in lines] == [("S-0001", DECISION)]

    def test_it_holds_the_story_that_touched_it_with_its_commit(self, checkout: Checkout) -> None:
        touched = document(checkout, "work.txt")["touched_by"]
        assert [(each["id"], each["commit"], each["title"]) for each in touched] == [
            ("S-0001", checkout.story, STORY_TITLE)
        ]

    def test_it_holds_the_task_that_touched_it_with_its_commit(self, checkout: Checkout) -> None:
        touched = document(checkout, "work.txt")["touched_by"]
        assert [(task["id"], task["commit"]) for task in touched[0]["tasks"]] == [
            ("T-0001", checkout.task)
        ]


@pytest.mark.parametrize("item", ["S-0001", "gate", "work.txt"], ids=["story", "term", "file"])
class TestEachDocument:
    def test_it_is_printed_canonical(self, checkout: Checkout, item: str) -> None:
        printed = about(checkout, item, "--format", "json").out
        assert printed == canonical(printed)

    def test_a_second_run_prints_the_same_bytes(self, checkout: Checkout, item: str) -> None:
        first = about(checkout, item, "--format", "json").out
        assert about(checkout, item, "--format", "json").out == canonical(first)

    def test_the_text_format_prints_what_no_format_prints(
        self, checkout: Checkout, item: str
    ) -> None:
        text = about(checkout, item, "--format", "text").out
        assert text == about(checkout, item).out != ""


class TestTheFormatRefused:
    def test_a_format_that_is_neither_is_refused_naming_both(self, checkout: Checkout) -> None:
        assert "--format 'xml' is not text or json, the two formats of about" in (
            about(checkout, "S-0001", "--format", "xml").err
        )

    def test_it_exits_with_two(self, checkout: Checkout) -> None:
        assert about(checkout, "S-0001", "--format", "xml").status == 2

    def test_it_prints_nothing(self, checkout: Checkout) -> None:
        assert about(checkout, "S-0001", "--format", "xml").out == ""


class TestTheTextIsUnchanged:
    def test_it_starts_with_the_id_and_the_title(self, checkout: Checkout) -> None:
        assert about(checkout, "S-0001").out.startswith(f"S-0001  {STORY_TITLE}\n")
