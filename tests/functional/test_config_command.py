"""The criterion of the configuration set through fgraph: `fgraph config set`, then `config show`.

The record holds no `config.toml`. Run end to end on a record in a temporary directory, through
the file adapters of the package.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, read_config, run

pytestmark = [
    pytest.mark.functional,
    pytest.mark.xfail(strict=True, reason="S-0045: config is no command yet"),
]

NOW = datetime(2026, 1, 1, tzinfo=UTC)
SET_ENABLED = ["config", "set", "development.enabled", "true"]
SHOW = ["config", "show"]


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
    """A directory whose record holds no config.toml."""
    (tmp_path / ".fgraph").mkdir()
    return tmp_path


class TestTheDevelopmentEnabledSetOnARecordWithoutAConfigFile:
    @pytest.fixture
    def enabled(self, project: Path) -> Outcome:
        return fgraph(SET_ENABLED, project)

    def test_set_exits_with_zero(self, enabled: Outcome) -> None:
        assert enabled.status == 0

    def test_show_then_lists_development_enabled_as_true(
        self, enabled: Outcome, project: Path
    ) -> None:
        assert "development.enabled = true" in fgraph(SHOW, project).out.splitlines()
