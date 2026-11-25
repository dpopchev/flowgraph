"""The criterion of S-0109: a file of the record the model refuses is said in one line, exit 2.

The line names the file and the key or the state in the words of fgraph, with no line of the
validator and no link to errors.pydantic.dev. Run end to end on a record in a temporary directory,
through the file adapters of the package.
"""

import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import tomli_w

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)

# The commands that write the record, each of which must exit 0.
RECORD = [
    ["add", "story", "a title", "--given", "a", "--when", "b", "--then", "c"],
    ["add", "feature", "a feature title", "--criterion", "a developer sees it"],
    ["add", "term", "gate", "--means", "a check every deliverable passes"],
]

# Each: the edit of the file, what the file holds and the words said after its name.
CASES = [
    pytest.param(
        ("items/S-0001.toml", "state", "blocked"),
        "Story",
        "started is missing, which the state blocked takes",
        id="blocked",
    ),
    pytest.param(
        ("items/S-0001.toml", "state", "doing"),
        "Story",
        'state is "doing": it takes backlog, started, blocked, completed or removed',
        id="unknown-state",
    ),
    pytest.param(
        ("items/S-0001.toml", "token", "x"),
        "Story",
        "token is no key of the state backlog",
        id="token",
    ),
    pytest.param(
        ("items/F-0001.toml", "token", "x"),
        "Feature",
        "token is no key of the state backlog",
        id="feature-token",
    ),
    pytest.param(
        ("terms/gate.toml", "token", "x"),
        "term",
        "token is no key of the file",
        id="term-token",
    ),
    pytest.param(
        ("queue.toml", None, None),
        "queue",
        "token is no key of the file",
        id="queue-token",
    ),
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
    place: Any = held
    for key in keys[:-1]:
        place = place[key]
    place[keys[-1]] = value
    path.write_text(tomli_w.dumps(held), "utf-8")


def edit(root: Path, name: str, key: str | None, value: str | None) -> Path:
    """Apply the edit of one case to the record and return the file it touched."""
    path = root / ".fgraph" / name
    if key is None:
        path.write_text("backlog = []\ntoken = 'x'\n", "utf-8")
    else:
        rewritten(path, value, key)
    return path


@pytest.fixture
def record(tmp_path: Path) -> Path:
    """A record written by the commands: a Story, a Feature and a term."""
    for argv in RECORD:
        done = fgraph(argv, tmp_path)
        assert done.status == 0, done.err
    return tmp_path


@pytest.mark.parametrize(("edited", "noun", "said"), CASES)
def test_status_of_a_file_with_a_key_or_a_state_it_does_not_take_names_them_in_one_line(
    record: Path, edited: tuple[str, str | None, str | None], noun: str, said: str
) -> None:
    path = edit(record, *edited)
    refused = fgraph(["status"], record)
    expected = (2, [f"fgraph: error: {path} holds no {noun}: {said}"])
    assert (refused.status, refused.err.splitlines()[-1:]) == expected


@pytest.mark.parametrize(("edited", "noun", "said"), CASES)
def test_the_refusal_prints_no_line_of_the_validator(
    record: Path, edited: tuple[str, str | None, str | None], noun: str, said: str
) -> None:
    edit(record, *edited)
    refused = fgraph(["status"], record)
    assert len(refused.err.splitlines()) == 2


def test_status_reads_the_record_as_the_commands_wrote_it(record: Path) -> None:
    assert fgraph(["status"], record).status == 0
