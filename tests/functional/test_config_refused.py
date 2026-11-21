"""A `config.toml` fgraph refuses: every command exits 2 naming the file and the key.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
ADD_STORY = [
    *("add", "story", "a story title"),
    *("--given", "a state", "--when", "an action", "--then", "another"),
]
STORY_FILE = Path(".fgraph") / "items" / "S-0001.toml"


@dataclass(frozen=True)
class Outcome:
    """What one run of the command left: its exit status, its output and its error output."""

    status: int
    out: str
    err: str


def fgraph(argv: Sequence[str], cwd: Path) -> Outcome:
    """Run the command in cwd, whose record is `.fgraph/`, on the files of that record."""
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
        load_config=read_config,
    )
    return Outcome(status, "".join(out), "".join(err))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A directory whose record holds a config.toml with a key the configuration has not."""
    (tmp_path / ".fgraph").mkdir()
    (tmp_path / ".fgraph" / "config.toml").write_text(
        "[development]\nenable = true\n", encoding="utf-8"
    )
    return tmp_path


@pytest.mark.parametrize(
    "argv",
    [[], ["status"], ["show", "S-0001"], ADD_STORY, ["watch", "--count", "1"]],
    ids=["no-command", "status", "show", "add", "watch"],
)
def test_a_command_on_a_config_refused_exits_with_two_naming_the_key(
    argv: list[str], project: Path
) -> None:
    outcome = fgraph(argv, project)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (
        2,
        f"fgraph: error: {project / '.fgraph' / 'config.toml'}:"
        " development.enable is no key of the configuration",
    )


def test_a_write_on_a_config_refused_writes_nothing(project: Path) -> None:
    fgraph(ADD_STORY, project)
    assert not (project / STORY_FILE).exists()
