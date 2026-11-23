"""The criterion of S-0116: one command prints the brief of a work item, as text and as JSON.

Run end to end through `run` on a real git repository in a temporary directory, never a faked
git; the identity of its commits comes from the environment and no git config is read.
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
CHECK = ("--check", "make test")
RELATED = ("--depends-on", "S-0001", "--about", "gate", "--complexity", "medium")
MEANING = "a check every deliverable passes before it lands"
GOVERNING = "the gate holds no state"
FEATURE_DECISION = "the gate is one check"
ITEM_DECISION = "the gate is read once"
OUTPUT = "changed: src/gate.py holds the gate"
IDENTITY = {
    "GIT_AUTHOR_NAME": "a developer",
    "GIT_AUTHOR_EMAIL": "developer@example.com",
    "GIT_COMMITTER_NAME": "a developer",
    "GIT_COMMITTER_EMAIL": "developer@example.com",
}
RECORD = [
    ["add", "term", "gate", "--means", MEANING],
    ["add", "feature", "the gate", "--criterion", "a criterion"],
    ["note", "F-0001", "--decision", FEATURE_DECISION],
    ["add", "story", "the first story", *CRITERION],
    ["add", "task", "a first task", "--parent", "S-0001", "--output", "an output"],
    ["start", "S-0001"],
    ["start", "T-0001"],
    ["complete", "T-0001"],
    ["complete", "S-0001"],
    ["note", "S-0001", "--decision", GOVERNING, "--governs", "src/gate.py"],
    ["config", "set", "development.enabled", "true"],
    ["add", "story", "the second story", *CRITERION, "--parent", "F-0001", *RELATED],
    ["add", "task", "a second task", "--parent", "S-0002", "--output", OUTPUT, *CHECK],
    ["note", "S-0002", "--decision", ITEM_DECISION],
    ["add", "story", "the third story", *CRITERION],
    ["start", "F-0001", "--slug", "brief-me", "--agent", "sonnet-a1"],
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


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
            now=lambda: NOW,
            open_git=open_git,
            load_config=read_config,
        )
    except SystemExit as refused:  # argparse refuses an option it does not know, before the run
        status = int(str(refused.code))
    return Outcome(status, "".join(out), "".join(err))


def git(cwd: Path, *args: str) -> str:
    """The output of the git command run in cwd, stripped; fails the test on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


@pytest.fixture(scope="module")
def checkout(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """A repository on main whose record holds S-0001 completed, S-0002 started and S-0003."""
    base = tmp_path_factory.mktemp("brief").resolve()
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
        git(path, "commit", "--quiet", "--allow-empty", "--message", "chore: start the project")
        for argv in RECORD:
            made = fgraph(argv, path)
            assert made.status == 0, f"{' '.join(argv)}: {made.err}"
        yield path


def worktree_of(checkout: Path) -> Path:
    """The worktree of S-0002, beside the checkout in its sibling container."""
    return checkout.parent / "project.worktrees" / "S-0002-brief-me"


def brief(checkout: Path, *argv: str) -> Outcome:
    """The outcome of fgraph brief with the arguments, run in the checkout."""
    return fgraph(["brief", *argv], checkout)


def shown(checkout: Path, item: str) -> str:
    """The text fgraph show prints of the item."""
    return fgraph(["show", item], checkout).out


class TestTheBriefAsText:
    @pytest.fixture
    def printed(self, checkout: Path) -> Outcome:
        return brief(checkout, "S-0002")

    def test_it_exits_with_zero(self, printed: Outcome) -> None:
        assert printed.status == 0

    def test_it_starts_with_the_text_of_show(self, printed: Outcome, checkout: Path) -> None:
        assert printed.out.startswith(shown(checkout, "S-0002"))

    def test_it_lists_the_branch_and_the_worktree(self, printed: Outcome, checkout: Path) -> None:
        worktree = worktree_of(checkout)
        assert f"Worktree\n  branch       wi/S-0002-brief-me\n  path         {worktree}\n" in (
            printed.out
        )

    def test_it_lists_the_feature(self, printed: Outcome) -> None:
        assert "Feature\n  F-0001  InProgress  the gate\n" in printed.out

    def test_it_lists_the_knowledge_of_the_feature(self, printed: Outcome) -> None:
        assert f"  Knowledge (1)\n    decision  2026-01-01  {FEATURE_DECISION}\n" in printed.out

    def test_it_lists_the_lines_that_govern_a_file_a_task_names(self, printed: Outcome) -> None:
        assert f"Governed by\n  decision  2026-01-01  S-0001  {GOVERNING}\n" in printed.out

    def test_it_lists_the_terms_with_their_meaning(self, printed: Outcome) -> None:
        assert f"Terms (1)\n  gate  {MEANING}\n" in printed.out


class TestTheBriefOfBacklogAsText:
    def test_it_prints_exactly_what_show_prints(self, checkout: Path) -> None:
        assert brief(checkout, "S-0003").out == shown(checkout, "S-0003")


class TestTheBriefRefusedAsText:
    @pytest.mark.parametrize("item", ["F-0001", "T-0001"])
    def test_an_id_that_is_no_work_item_is_refused_naming_the_kinds(
        self, checkout: Path, item: str
    ) -> None:
        assert "is no Story, Upkeep, Bug or Spike id" in brief(checkout, item).err


def document(checkout: Path, item: str) -> Any:
    """The JSON fgraph brief prints of the item, parsed."""
    return json.loads(brief(checkout, item, "--format", "json").out)


class TestTheBriefAsJson:
    def test_it_holds_the_branch(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["branch"] == "wi/S-0002-brief-me"

    def test_it_holds_the_worktree(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["worktree"] == str(worktree_of(checkout))

    def test_it_holds_the_agent(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["agent"] == "sonnet-a1"

    def test_it_holds_the_complexity(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["complexity"] == "medium"

    def test_it_holds_the_given_of_the_criterion(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["criterion"]["given"] == "a state"

    def test_it_holds_each_work_item_it_depends_on_with_its_bucket(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["depends_on"] == [
            {"bucket": "Completed", "id": "S-0001"}
        ]

    def test_it_waits_for_none(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["waits_for"] == []

    def test_it_holds_the_id_of_the_feature(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["feature"]["id"] == "F-0001"

    def test_it_holds_the_knowledge_of_the_feature(self, checkout: Path) -> None:
        lines = document(checkout, "S-0002")["feature"]["knowledge"]
        assert [line["text"] for line in lines] == [FEATURE_DECISION]

    def test_it_holds_the_item_of_the_line_that_governs(self, checkout: Path) -> None:
        lines = document(checkout, "S-0002")["governed_by"]
        assert [line["item"] for line in lines] == ["S-0001"]

    def test_it_holds_the_terms(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["terms"] == [{"meaning": MEANING, "name": "gate"}]

    def test_it_holds_the_check_of_the_first_task(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["tasks"][0]["check"] == "make test"

    def test_it_holds_the_expected_output_of_the_first_task(self, checkout: Path) -> None:
        assert document(checkout, "S-0002")["tasks"][0]["expected_output"] == OUTPUT

    def test_it_is_printed_with_sorted_keys_an_indent_of_two_and_a_newline(
        self, checkout: Path
    ) -> None:
        printed = brief(checkout, "S-0002", "--format", "json").out
        assert printed == json.dumps(json.loads(printed), indent=2, sort_keys=True) + "\n"


class TestTheBriefOfBacklogAsJson:
    @pytest.mark.parametrize("key", ["branch", "worktree", "feature"])
    def test_a_part_it_has_none_of_is_null(self, checkout: Path, key: str) -> None:
        assert document(checkout, "S-0003")[key] is None


class TestTheFormatRefused:
    def test_a_format_that_is_neither_is_refused_naming_both(self, checkout: Path) -> None:
        assert "is not text or json, the two formats of brief" in (
            brief(checkout, "S-0002", "--format", "xml").err
        )
