"""fgraph about given a wrong id is refused, and writes nothing: a text that is no id in its
own words, an id the record does not hold as fgraph show refuses it.

Run end to end on a record in a temporary directory, through the file adapters of the package.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from flowgraph.cli import open_files, run

pytestmark = pytest.mark.functional

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def refusal(command: str, text: str, cwd: Path) -> tuple[int, list[str]]:
    """The exit status of the command on that text in cwd, and the last line of its error output."""
    (cwd / ".fgraph").mkdir(exist_ok=True)
    err: list[str] = []
    status = run(
        [command, text],
        cwd,
        Path.is_dir,
        lambda _: None,
        err.append,
        open_store=open_files,
        open_git=lambda _: None,
        now=lambda: NOW,
    )
    return status, "".join(err).splitlines()[-1:]


@pytest.mark.parametrize("text", ["F-0000", "S-0009", "F-0009"])
def test_about_refuses_what_show_refuses_in_the_same_words(text: str, tmp_path: Path) -> None:
    assert refusal("about", text, tmp_path) == refusal("show", text, tmp_path)


@pytest.mark.parametrize("text", ["X-0001", "T-0001", "S-0000"])
def test_about_of_a_text_that_is_no_id_is_refused_in_its_own_words(
    text: str, tmp_path: Path
) -> None:
    assert refusal("about", text, tmp_path) == (
        2,
        [f"fgraph: error: {text!r} is no Story, Upkeep, Bug, Spike or Feature id"],
    )


def test_about_of_an_id_the_record_holds_none_of_exits_with_two(tmp_path: Path) -> None:
    assert refusal("about", "S-0009", tmp_path)[0] == 2
