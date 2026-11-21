"""The adapter that runs the gate of a landing, against a real command in a temporary directory."""

from pathlib import Path

import pytest

from flowgraph.gate import run_gate

pytestmark = pytest.mark.edge


def test_a_command_that_succeeds_exits_with_zero(tmp_path: Path) -> None:
    assert run_gate("true", tmp_path) == 0


def test_a_command_that_fails_exits_with_its_status(tmp_path: Path) -> None:
    assert run_gate("exit 3", tmp_path) == 3


def test_the_command_runs_in_the_directory(tmp_path: Path) -> None:
    (tmp_path / "work.txt").touch()
    assert run_gate("test -f work.txt", tmp_path) == 0


def test_the_command_line_is_read_by_the_shell(tmp_path: Path) -> None:
    run_gate("echo one > said.txt && echo two >> said.txt", tmp_path)
    assert (tmp_path / "said.txt").read_text(encoding="utf-8") == "one\ntwo\n"


def test_the_output_of_the_command_is_written_as_the_command_wrote_it(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    run_gate("echo checked", tmp_path)
    assert capfd.readouterr().out == "checked\n"


def test_the_error_output_of_the_command_is_written_as_the_command_wrote_it(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    run_gate("echo broken >&2", tmp_path)
    assert capfd.readouterr().err == "broken\n"
