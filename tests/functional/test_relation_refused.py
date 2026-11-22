"""The criterion of S-0078: a record whose relation names nothing or closes a cycle is refused.

A file of the record edited by hand or merged to name an id or a term that is not in the record,
or to close a cycle of what depends on what or of the kinds between terms, makes every command
exit with 2 and one line naming the file and the relation, never a Python traceback, and writes
nothing. Run end to end on a record in a temporary directory, through the file adapters of the
package.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
BUILT = [
    ["add", "term", "gate", "--means", "a check"],
    ["add", "term", "hall", "--means", "a room"],
    ["add", "term", "door", "--means", "a way in"],
    ["relate", "door", "is-a", "gate"],
    ["relate", "door", "part-of", "hall"],
    ["add", "feature", "a feature", "--criterion", "a developer sees it"],
    ["add", "story", "the first title", *CRITERION, "--parent", "F-0001"],
    ["add", "story", "the second title", *CRITERION, "--depends-on", "S-0001"],
    ["note", "S-0002", "--finding", "a text", "--about", "gate"],
]
# Added by a second run: it is no relation of the first record and names a term the second lacks.
FILED = ["add", "story", "the third title", *CRITERION, "--filed-during", "S-0001"]
ABOUT = ["add", "story", "the fourth title", *CRITERION, "--about", "gate"]
REMOVED = ["remove", "S-0004", "--reason", "a reason", "--superseded-by", "S-0001"]


def fgraph(argv: list[str], cwd: Path) -> tuple[int, str]:
    """Run the command in cwd, whose record is `.fgraph/`: its exit status and error output."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    err: list[str] = []
    status = run(
        argv,
        cwd,
        Path.is_dir,
        lambda _: None,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: NOW,
    )
    return status, "".join(err)


def replacing(old: str, new: str) -> Callable[[str], str]:
    """The edit that puts new for the first old of a file."""
    return lambda text: text.replace(old, new, 1)


def replacing_last(old: str, new: str) -> Callable[[str], str]:
    """The edit that puts new for the last old of a file."""
    return lambda text: new.join(text.rsplit(old, 1))


def beginning(line: str) -> Callable[[str], str]:
    """The edit that puts the line before the first table of a file."""
    return lambda text: f"{line}\n{text}"


@pytest.fixture
def record(tmp_path: Path) -> Path:
    """The record of three terms, a Feature, two Stories and a finding, as fgraph wrote it."""
    for argv in [*BUILT, FILED, ABOUT, REMOVED]:
        fgraph(argv, tmp_path)
    return tmp_path / ".fgraph"


def broken(record: Path, name: str, edit: Callable[[str], str]) -> Path:
    """Edit the file of the record of that name and give its path."""
    path = record / name
    path.write_text(edit(path.read_text(encoding="utf-8")), encoding="utf-8")
    return path


def files_of(record: Path) -> dict[Path, str]:
    """The text of every file of the record, by its path."""
    return {path: path.read_text(encoding="utf-8") for path in record.rglob("*") if path.is_file()}


def lacking(relation: str, named: str) -> str:
    """What a refusal says of a relation that names something the record does not hold."""
    return f"{relation} names {named}, which is not in the record"


NAMES_NOTHING = [
    ("items/S-0001.toml", replacing('"F-0001"', '"F-0099"'), lacking("parent", "F-0099")),
    ("items/S-0002.toml", replacing('"S-0001",', '"S-0099",'), lacking("depends on", "S-0099")),
    ("items/S-0003.toml", replacing('"S-0001"', '"S-0099"'), lacking("filed during", "S-0099")),
    ("items/S-0004.toml", replacing('"S-0001"', '"S-0099"'), lacking("superseded by", "S-0099")),
    ("items/S-0002.toml", beginning('amends = "S-0099"'), lacking("amends", "S-0099")),
    ("items/S-0004.toml", replacing('"gate"', '"nope"'), lacking("about", "nope")),
    ("items/S-0002.toml", replacing_last('"gate"', '"nope"'), lacking("about", "nope")),
    ("items/F-0001.toml", beginning('about = ["nope"]'), lacking("about", "nope")),
    ("terms/door.toml", replacing('"gate"', '"nope"'), lacking("is a", "nope")),
    ("terms/door.toml", replacing('"hall"', '"nope"'), lacking("part of", "nope")),
]
IDS = [
    "parent",
    "depends-on",
    "filed-during",
    "superseded-by",
    "amends",
    "about-of-an-item",
    "about-of-a-line",
    "about-of-a-feature",
    "is-a",
    "part-of",
]


@pytest.mark.parametrize(("name", "edit", "said"), NAMES_NOTHING, ids=IDS)
def test_status_of_a_relation_that_names_nothing_exits_with_two_naming_the_file_and_the_id(
    name: str, edit: Callable[[str], str], said: str, record: Path
) -> None:
    path = broken(record, name, edit)
    status, err = fgraph(["status"], record.parent)
    assert (status, err.splitlines()[-1:]) == (2, [f"fgraph: error: {path}: {said}"])


CLOSES_CYCLE = [
    (
        "items/S-0001.toml",
        beginning('depends_on = ["S-0002"]'),
        "depends on closes a cycle: S-0001 -> S-0002 -> S-0001",
        "items/S-0001.toml",
    ),
    (
        "terms/gate.toml",
        beginning('is_a = ["door"]'),
        "is a closes a cycle: door -> gate -> door",
        "terms/door.toml",
    ),
    (
        "terms/hall.toml",
        beginning('part_of = ["door"]'),
        "part of closes a cycle: door -> hall -> door",
        "terms/door.toml",
    ),
]


@pytest.mark.parametrize(
    ("name", "edit", "said", "named"), CLOSES_CYCLE, ids=["depends-on", "is-a", "part-of"]
)
def test_status_of_a_relation_that_closes_a_cycle_exits_with_two_naming_the_file_and_the_cycle(
    name: str, edit: Callable[[str], str], said: str, named: str, record: Path
) -> None:
    broken(record, name, edit)
    status, err = fgraph(["status"], record.parent)
    assert (status, err.splitlines()[-1:]) == (2, [f"fgraph: error: {record / named}: {said}"])


def test_a_write_of_a_record_with_a_relation_that_names_nothing_leaves_every_file_as_it_was(
    record: Path,
) -> None:
    broken(record, "items/S-0002.toml", replacing('"S-0001",', '"S-0099",'))
    held = files_of(record)
    fgraph(["add", "story", "another title", *CRITERION], record.parent)
    assert files_of(record) == held


def test_status_of_a_record_whose_relations_all_name_what_it_holds_exits_with_zero(
    record: Path,
) -> None:
    assert fgraph(["status"], record.parent)[0] == 0
