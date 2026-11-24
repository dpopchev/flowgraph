"""The criterion of B-0026: a time of a file with no offset is refused at the read, exit 2.

The refusal is one line naming the file, the key and what is written, with no traceback. Run end
to end on a record in a temporary directory, through the file adapters of the package.
"""

import tomllib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
import tomli_w

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
DAY = date(2026, 10, 11)
XFAIL = pytest.mark.xfail(strict=True, reason="B-0026: a time of a file with no offset is read")

# The commands that write the record, each of which must exit 0.
RECORD = [
    ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"],
    ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"],
    ["note", "S-0001", "--finding", "the store is plain files"],
    ["add", "feature", "a feature title", "--criterion", "a developer sees it"],
    ["add", "term", "gate", "--means", "a check every deliverable passes"],
]

# The file, the keys to the time in it, what the file holds and the key named in the line.
CASES = [
    ("items/S-0001.toml", ("created",), "Story", "created"),
    ("items/S-0001.toml", ("knowledge", 0, "noted"), "Story", "noted"),
    ("items/F-0001.toml", ("created",), "Feature", "created"),
    ("terms/gate.toml", ("added",), "term", "added"),
]


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: list[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
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
        now=lambda: NOW,
    )
    return Outcome(status, "".join(out), "".join(err))


def rewritten(path: Path, value: object, *keys: str | int) -> None:
    """Write the file again with the value at the end of the keys."""
    held = tomllib.loads(path.read_text("utf-8"))
    place = held
    for key in keys[:-1]:
        place = place[key]
    place[keys[-1]] = value
    path.write_text(tomli_w.dumps(held), "utf-8")


def line(path: Path, noun: str, key: str, written: str = "2026-10-11") -> str:
    """The one line of the refusal of a time written with no offset."""
    return (
        f"fgraph: error: {path} holds no {noun}: {key} = {written} is a time with no offset: "
        "write it with one, as 2026-01-01 09:00:00+00:00"
    )


def story_file(cwd: Path) -> Path:
    """The file of S-0001."""
    return cwd / ".fgraph" / "items" / "S-0001.toml"


@pytest.fixture
def record(tmp_path: Path) -> Path:
    """A record written by the commands: two Stories, a finding, a Feature and a term."""
    for argv in RECORD:
        done = fgraph(argv, tmp_path)
        assert done.status == 0, done.err
    return tmp_path


@XFAIL
@pytest.mark.parametrize(("name", "keys", "noun", "key"), CASES)
def test_status_refuses_a_day_alone_naming_the_file(
    record: Path, name: str, keys: tuple[str | int, ...], noun: str, key: str
) -> None:
    path = record / ".fgraph" / name
    rewritten(path, DAY, *keys)
    refused = fgraph(["status"], record)
    assert (refused.status, refused.err.splitlines()[-1:]) == (2, [line(path, noun, key)])


@XFAIL
@pytest.mark.parametrize(
    "argv", [["knowledge"], ["show", "S-0002"], ["amend", "S-0001", "--title", "another title"]]
)
def test_every_command_refuses_a_day_alone_in_a_story(record: Path, argv: list[str]) -> None:
    rewritten(story_file(record), DAY, "created")
    refused = fgraph(argv, record)
    expected = (2, [line(story_file(record), "Story", "created")])
    assert (refused.status, refused.err.splitlines()[-1:]) == expected


@XFAIL
def test_an_amend_refused_leaves_the_file_as_it_was_written(record: Path) -> None:
    rewritten(story_file(record), DAY, "created")
    before = story_file(record).read_text("utf-8")
    fgraph(["amend", "S-0001", "--title", "another title"], record)
    assert story_file(record).read_text("utf-8") == before


@XFAIL
def test_status_refuses_a_time_with_no_offset_naming_what_is_written(record: Path) -> None:
    rewritten(story_file(record), datetime(2026, 10, 11, 9), "created")
    refused = fgraph(["status"], record)
    expected = (2, [line(story_file(record), "Story", "created", "2026-10-11 09:00:00")])
    assert (refused.status, refused.err.splitlines()[-1:]) == expected


def test_status_reads_the_record_as_the_commands_wrote_it(record: Path) -> None:
    assert fgraph(["status"], record).status == 0


def test_status_reads_a_time_written_with_an_offset(record: Path) -> None:
    rewritten(
        story_file(record),
        datetime(2026, 10, 11, 9, tzinfo=timezone(timedelta(hours=2))),
        "created",
    )
    assert fgraph(["status"], record).status == 0
