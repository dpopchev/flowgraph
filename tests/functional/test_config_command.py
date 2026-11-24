"""The criterion of the configuration set through fgraph: `fgraph config set`, then `config show`.

The record holds no `config.toml`. Run end to end on a record in a temporary directory, through
the file adapters of the package.
"""

import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, read_config, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)
SET_ENABLED = ["config", "set", "development.enabled", "true"]
SHOW = ["config", "show"]
CONFIG = Path(".fgraph") / "config.toml"
LIMITED = "[development]\nenabled = true\nparallel = 2\n"
UNCOMMITTED = "[git]\ncommit = false\n"


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

    def test_set_says_the_key_with_its_value_and_warns_of_nothing(self, enabled: Outcome) -> None:
        assert (enabled.out, enabled.err) == ("set development.enabled = true\n", "")

    def test_the_config_file_holds_that_key_alone(self, enabled: Outcome, project: Path) -> None:
        assert (project / CONFIG).read_text(encoding="utf-8") == "[development]\nenabled = true\n"


def test_show_lists_every_key_at_its_default_on_a_record_without_a_config_file(
    project: Path,
) -> None:
    assert fgraph(SHOW, project) == Outcome(
        0,
        "git.commit = true\n"
        "development.enabled = false\n"
        "development.parallel = none\n"
        'development.merge = "merge-commit"\n'
        "development.gate = none\n"
        'development.driver = "developer"\n'
        "delivery.push = false\n"
        'delivery.tag = "none"\n'
        "archive.board = none\n",
        "",
    )


def test_show_writes_no_config_file(project: Path) -> None:
    fgraph(SHOW, project)
    assert not (project / CONFIG).exists()


def test_a_set_keeps_the_other_keys_of_the_config_file(project: Path) -> None:
    (project / CONFIG).write_text(LIMITED, encoding="utf-8")
    fgraph(["config", "set", "development.gate", "make check"], project)
    assert tomllib.loads((project / CONFIG).read_text(encoding="utf-8")) == {
        "development": {"enabled": True, "parallel": 2, "gate": "make check"}
    }


def test_a_key_is_taken_back_to_its_default_by_setting_that_default(project: Path) -> None:
    (project / CONFIG).write_text(LIMITED, encoding="utf-8")
    fgraph(["config", "set", "development.enabled", "false"], project)
    assert fgraph(SHOW, project).out.splitlines()[1:3] == [
        "development.enabled = false",
        "development.parallel = 2",
    ]


class TestTheGateTakenBackWithConfigUnset:
    @pytest.fixture
    def unset(self, project: Path) -> Outcome:
        (project / CONFIG).write_text(f'{LIMITED}gate = "make check"\n', encoding="utf-8")
        return fgraph(["config", "unset", "development.gate"], project)

    def test_unset_says_the_key_is_none_and_warns_of_nothing(self, unset: Outcome) -> None:
        assert unset == Outcome(0, "unset development.gate = none\n", "")

    def test_show_then_lists_development_gate_as_none(self, unset: Outcome, project: Path) -> None:
        assert "development.gate = none" in fgraph(SHOW, project).out.splitlines()

    def test_the_config_file_keeps_the_other_keys(self, unset: Outcome, project: Path) -> None:
        assert tomllib.loads((project / CONFIG).read_text(encoding="utf-8")) == {
            "development": {"enabled": True, "parallel": 2}
        }


def test_the_push_of_a_landing_set_is_listed_by_show_as_true(project: Path) -> None:
    fgraph(["config", "set", "delivery.push", "true"], project)
    assert "delivery.push = true" in fgraph(SHOW, project).out.splitlines()


def test_the_push_of_a_landing_unset_is_back_to_false_with_no_delivery_table(
    project: Path,
) -> None:
    (project / CONFIG).write_text(f"{LIMITED}[delivery]\npush = true\n", encoding="utf-8")
    unset = fgraph(["config", "unset", "delivery.push"], project)
    assert (unset.out, tomllib.loads((project / CONFIG).read_text(encoding="utf-8"))) == (
        "unset delivery.push = false\n",
        {"development": {"enabled": True, "parallel": 2}},
    )


def test_an_unset_of_no_key_of_the_configuration_exits_with_two_naming_it(project: Path) -> None:
    outcome = fgraph(["config", "unset", "development.gates"], project)
    assert (outcome.status, outcome.err.splitlines()[-1]) == (
        2,
        "fgraph: error: development.gates is no key of the configuration",
    )


@pytest.mark.parametrize(
    ("content", "argv", "why"),
    [
        (
            "",
            ["config", "set", "development.enable", "true"],
            "development.enable is no key of the configuration",
        ),
        (
            "",
            ["config", "set", "development.parallel", "0"],
            "development.parallel is 0: it takes a whole number of 1 or more",
        ),
        (
            "",
            ["config", "set", "development.enabled", "yes"],
            'development.enabled is "yes": it takes true or false',
        ),
        (
            UNCOMMITTED,
            SET_ENABLED,
            "development.enabled is true while git.commit is false:"
            " the development needs the commits of the record",
        ),
    ],
    ids=["no-key", "no-count", "no-truth", "development-on-with-the-commits-off"],
)
def test_a_set_the_configuration_refuses_exits_with_two_naming_the_key(
    project: Path, content: str, argv: list[str], why: str
) -> None:
    (project / CONFIG).write_text(content, encoding="utf-8")
    outcome = fgraph(argv, project)
    assert (outcome.status, outcome.out, outcome.err.splitlines()[-1]) == (
        2,
        "",
        f"fgraph: error: {why}",
    )


def test_a_set_refused_leaves_the_config_file_as_it_was(project: Path) -> None:
    (project / CONFIG).write_text(UNCOMMITTED, encoding="utf-8")
    fgraph(SET_ENABLED, project)
    assert (project / CONFIG).read_text(encoding="utf-8") == UNCOMMITTED


def test_a_set_refused_on_a_record_without_a_config_file_makes_none(project: Path) -> None:
    fgraph(["config", "set", "development.parallel", "0"], project)
    assert [path.name for path in (project / ".fgraph").iterdir()] == []
