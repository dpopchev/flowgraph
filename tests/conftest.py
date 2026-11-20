"""The report of a test run: with --slowest-file, the run writes its slowest tests there.

The file is a markdown table, one row per test -- its module, its name inside the module, and its
seconds over setup, call and teardown -- the slowest first, rewritten by every run that passes the
option. `make test` passes it; other runs leave the last report alone.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

SLOWEST = 10


@dataclass(frozen=True)
class Timing:
    """One test of the run and the seconds it took over setup, call and teardown."""

    nodeid: str
    seconds: float


def totals(reports: Iterable[pytest.TestReport]) -> dict[str, float]:
    """Sum each test's phase durations by its node id."""
    seconds: dict[str, float] = {}
    for report in reports:
        seconds[report.nodeid] = seconds.get(report.nodeid, 0.0) + report.duration
    return seconds


def slowest(seconds: Mapping[str, float], count: int) -> list[Timing]:
    """The count slowest tests, the slowest first."""
    ranked = sorted(seconds.items(), key=lambda item: item[1], reverse=True)
    return [Timing(nodeid, total) for nodeid, total in ranked[:count]]


def table(timings: Iterable[Timing]) -> str:
    """The markdown table of the timings; the node id splits at its first `::`.

    >>> print(table([Timing("tests/test_a.py::TestA::test_b", 0.25)]), end="")
    | module | test | seconds |
    |---|---|---:|
    | tests/test_a.py | TestA::test_b | 0.250 |
    """
    rows = [
        f"| {module} | {test} | {timing.seconds:.3f} |"
        for timing in timings
        for module, _, test in [timing.nodeid.partition("::")]
    ]
    return "\n".join(["| module | test | seconds |", "|---|---|---:|", *rows]) + "\n"


def write_slowest(path: Path, text: str) -> None:
    """Write the report, creating its folder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--slowest-file",
        metavar="PATH",
        default=None,
        help=f"write the {SLOWEST} slowest tests of this run to PATH as a markdown table",
    )


def pytest_terminal_summary(
    terminalreporter: pytest.TerminalReporter, config: pytest.Config
) -> None:
    path = config.getoption("slowest_file")
    if path is None:
        return
    reports = (
        report
        for reports in terminalreporter.stats.values()
        for report in reports
        if isinstance(report, pytest.TestReport)
    )
    write_slowest(Path(path), table(slowest(totals(reports), SLOWEST)))
